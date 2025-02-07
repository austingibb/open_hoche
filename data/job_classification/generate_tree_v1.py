import json
import time
import datetime
from ollama import Client

# --- Configuration ---
OLLAMA_IP = "127.0.0.1"          # Local Ollama server IP
OLLAMA_PORT = 11434              # Ollama port
MODEL_NAME = "deepseek-r1:14b"          # Model to use

JOB_ROLES_FILE = "data/job_classification/job_roles.txt"
NAICS_FILE = "data/job_classification/naics_industries.txt"

MAJOR_VERSION = 1
MINOR_VERSION = 0
PATCH_DATE = datetime.datetime.now().strftime("%Y/%m/%d")
HIERARCHY_PREFIX = f"hoche.2025_job_roles.V{MAJOR_VERSION}/{MINOR_VERSION}.{PATCH_DATE}"

# Create a custom Ollama client using the provided IP/port
client = Client(host=f"http://{OLLAMA_IP}:{OLLAMA_PORT}")

# --- File Parsing Functions ---

def read_job_roles(file_path):
    """Read job roles from a newline-delimited file."""
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def read_naics_industries(file_path):
    """
    Read NAICS industries from a newline-delimited file.
    Skip lines that are headers (single letters) or empty.
    """
    industries = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or (len(line) == 1 and line.isalpha()):
                continue
            industries.append(line)
    return industries

# --- LLM Query Function ---

def classify_job_role(job_role, naics_industries):
    """
    Use the Ollama local LLM to classify the job role.
    Constructs a prompt explaining OpenHoche and providing valid NAICS industries.
    """
    prompt = (
        f"OpenHoche is an open hierarchical object classification and heuristics engine. "
        f"It uses URIs of the form:\n"
        f"{HIERARCHY_PREFIX}.<NAICS industry>.<sector>.<service/subsector>...\n\n"
        "The following are valid NAICS industries:\n"
        f"{chr(10).join(naics_industries)}\n\n"
        "Job roles are specific to the USA. Please classify the following job role by "
        "returning a URI that fits the above framework. Avoid unnecessary duplication in higher-level "
        "segments while allowing lower-level duplication if needed.\n\n"
        f"Job Role: {job_role}\n"
    )
    try:
        response = client.generate(model=MODEL_NAME, prompt=prompt)
        uri = response.get("completion", "").strip()
        return uri if uri else None
    except Exception as e:
        print(f"[Error] Job Role '{job_role}': {e}")
        return None

# --- URI Analysis Function ---

def analyze_uris(uri_mapping):
    """
    Analyze the returned URIs and merge them into a hierarchical tree.
    Expected URI format:
      hoche.2025_job_roles.V<major>/<minor>.<YYYY>/<MM>/<DD>.<NAICS>.<sector>.<service>...
    """
    hierarchy_tree = {}
    for role, uri in uri_mapping.items():
        parts = uri.split(".")
        if len(parts) < 5:
            print(f"[Warning] URI '{uri}' for role '{role}' does not conform to expected format.")
            continue
        # Skip the first 4 segments to focus on classification parts.
        classification_parts = parts[4:]
        subtree = hierarchy_tree
        for part in classification_parts:
            if part not in subtree:
                subtree[part] = {}
            subtree = subtree[part]
        subtree.setdefault("_job_roles", []).append(role)
    return hierarchy_tree

# --- Main Script ---

def main():
    job_roles = read_job_roles(JOB_ROLES_FILE)
    naics_industries = read_naics_industries(NAICS_FILE)
    job_role_uri_mapping = {}

    for job_role in job_roles:
        print(f"[Info] Classifying '{job_role}'...")
        uri = classify_job_role(job_role, naics_industries)
        if uri:
            job_role_uri_mapping[job_role] = uri
            print(f"   → Received URI: {uri}")
        else:
            print("   → Failed to obtain URI.")
        time.sleep(1)  # Pause between requests

    # Save raw URI mappings
    with open("job_roles_hierarchy.json", "w") as f:
        json.dump(job_role_uri_mapping, f, indent=2)
    print("[Info] Saved job role URI mappings to 'job_roles_hierarchy.json'.")

    # Merge and analyze URI patterns
    hierarchy_tree = analyze_uris(job_role_uri_mapping)
    with open("merged_hierarchy.json", "w") as f:
        json.dump(hierarchy_tree, f, indent=2)
    print("[Info] Saved merged hierarchical data to 'merged_hierarchy.json'.")

if __name__ == "__main__":
    main()
