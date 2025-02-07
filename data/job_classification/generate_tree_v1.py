import requests
import json
import time
import datetime

# --- Configuration ---
OLLAMA_IP = "127.0.0.1"          # Local Ollama server IP
OLLAMA_PORT = 11434              # Assumed port for Ollama API
NAICS_INDUSTRIES = [
    "111", "112", "113"         # Replace with actual NAICS industry codes
]
JOB_ROLES = [
    "Software Engineer",
    "Software Architect",
    "Graphic Designer",
    "Data Analyst"
    # ... add all job roles
]

# Version and patch date for the hierarchy URI
MAJOR_VERSION = 1
MINOR_VERSION = 0
PATCH_DATE = datetime.datetime.now().strftime("%Y/%m/%d")
HIERARCHY_PREFIX = f"hoche.2025_job_roles.V{MAJOR_VERSION}/{MINOR_VERSION}.{PATCH_DATE}"

# --- Functions ---

def classify_job_role(job_role):
    """
    Send a plaintext prompt to the local LLM (Ollama) explaining OpenHoche and asking for a URI classification.
    """
    prompt = (
        "OpenHoche is an open hierarchical object classification and heuristics engine. "
        "It uses URIs of the form:\n"
        f"{HIERARCHY_PREFIX}.<NAICS industry>.<sector>.<service/subsector>....\n\n"
        "Job roles are specific to the USA. Please classify the following job role by "
        "returning a URI that fits the above framework. Avoid unnecessary duplication in higher-level "
        "segments while allowing lower-level duplication if needed.\n\n"
        f"Job Role: {job_role}\n"
    )

    url = f"http://{OLLAMA_IP}:{OLLAMA_PORT}/v1/generate"
    payload = {
        "prompt": prompt,
        "max_tokens": 150,
        # Add other API parameters as needed by your Ollama configuration
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        # Expecting the response to contain a 'completion' field with the URI
        uri = result.get("completion", "").strip()
        return uri if uri else None
    except Exception as e:
        print(f"[Error] Job Role '{job_role}': {e}")
        return None

def analyze_uris(uri_mapping):
    """
    Analyze and merge URIs to form a hierarchical tree.
    The tree is built using the segments after the patch date.
    """
    hierarchy_tree = {}
    for role, uri in uri_mapping.items():
        # Expected URI format:
        # hoche.2025_job_roles.V<major>/<minor>.<YYYY>/<MM>/<DD>.<NAICS>.<sector>.<service>...
        parts = uri.split(".")
        if len(parts) < 5:
            print(f"[Warning] URI '{uri}' for role '{role}' does not conform to expected format.")
            continue
        # Skip the first 4 parts (protocol, dataset, version, date) to get classification segments.
        classification_parts = parts[4:]
        subtree = hierarchy_tree
        for part in classification_parts:
            if part not in subtree:
                subtree[part] = {}
            subtree = subtree[part]
        # Collect job roles at the leaf node.
        subtree.setdefault("_job_roles", []).append(role)
    return hierarchy_tree

# --- Main Script ---

def main():
    job_role_uri_mapping = {}

    for job_role in JOB_ROLES:
        print(f"[Info] Classifying '{job_role}'...")
        uri = classify_job_role(job_role)
        if uri:
            job_role_uri_mapping[job_role] = uri
            print(f"   → Received URI: {uri}")
        else:
            print("   → Failed to obtain URI.")
        time.sleep(1)  # Wait between requests to avoid overloading the LLM

    # Save raw URI mappings
    with open("job_roles_hierarchy.json", "w") as f:
        json.dump(job_role_uri_mapping, f, indent=2)
    print("[Info] Saved job role URI mappings to 'job_roles_hierarchy.json'.")

    # Analyze and merge URI patterns
    hierarchy_tree = analyze_uris(job_role_uri_mapping)
    with open("merged_hierarchy.json", "w") as f:
        json.dump(hierarchy_tree, f, indent=2)
    print("[Info] Saved merged hierarchical data to 'merged_hierarchy.json'.")

if __name__ == "__main__":
    main()
