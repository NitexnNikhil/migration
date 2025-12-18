import os
import json
import requests
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

BATCH_SIZE = 500
THREADS = 6
OUTPUT_FILE = "scripts/upstash_dump.json"




# -------------------------------
# Load configuration
# -------------------------------
def get_config():
    load_dotenv()
    
    return {
        'src_url': os.getenv("SRC_REDIS_REST_URL"),
        'src_token': os.getenv("SRC_REDIS_REST_TOKEN")
    }


# -------------------------------
# Execute pipeline request
# -------------------------------
def execute_pipeline(url, token, commands):
    """Execute multiple Redis commands in a single HTTP request"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    resp = requests.post(
        url=f"{url}/pipeline",
        headers=headers,
        data=json.dumps(commands),
        timeout=60
    )
    
    if resp.status_code != 200:
        print(f"🚨 Pipeline failed: {resp.status_code} - {resp.text}")
        return None
    
    return resp.json()


# -------------------------------
# Scan all keys using REST API
# -------------------------------
def scan_all_keys(src_url, src_token):
    """Scan all keys efficiently using REST API"""
    all_keys = []
    cursor = "0"
    scan_count = 0
    
    headers = {
        "Authorization": f"Bearer {src_token}",
        "Content-Type": "application/json",
    }
    
    print("🔍 Scanning keys from source database...")
    
    while True:
        scan_count += 1
        
        resp = requests.post(
            url=f"{src_url}",
            headers=headers,
            data=json.dumps(["SCAN", cursor, "COUNT", str(BATCH_SIZE)]),
            timeout=30
        )
        
        if resp.status_code != 200:
            print(f"🚨 Scan failed: {resp.text}")
            break
        
        data = resp.json()
        result = data.get('result', [])
        
        if len(result) >= 2:
            cursor = str(result[0])
            keys = result[1]
            all_keys.extend(keys)
            
            if scan_count % 10 == 0:
                print(f"   Scanned {len(all_keys)} keys so far...")
        
        if cursor == "0":
            break
    
    print(f"✅ Total keys found: {len(all_keys)} (in {scan_count} scan operations)")
    return all_keys


# -------------------------------
# Read batch data with actual values
# -------------------------------
def read_batch_data(src_url, src_token, keys):
    """
    Read all key data including type, value, and TTL.
    Returns human-readable data suitable for JSON export.
    """
    if not keys:
        return {}
    
    # Build pipeline: TYPE, DUMP, PTTL for each key
    commands = []
    for key in keys:
        commands.append(["TYPE", key])
        commands.append(["DUMP", key])
        commands.append(["PTTL", key])
    
    results = execute_pipeline(src_url, src_token, commands)
    
    if not results:
        return {}
    
    # Parse results
    key_data = {}
    for i, key in enumerate(keys):
        type_idx = i * 3
        dump_idx = i * 3 + 1
        ttl_idx = i * 3 + 2
        
        key_type = results[type_idx].get('result', 'none')
        dump_result = results[dump_idx].get('result')
        ttl_result = results[ttl_idx].get('result', -1)
        
        # Skip if key doesn't exist
        if dump_result and dump_result != "null":
            key_data[key] = {
                'type': key_type,
                'dump': dump_result,  # Base64 serialized data
                'ttl': ttl_result if ttl_result > 0 else -1
            }
    
    return key_data


# -------------------------------
# Read a single batch
# -------------------------------
def read_batch(config, keys, batch_id, total_batches):
    """Read one batch of keys"""
    try:
        key_data = read_batch_data(config['src_url'], config['src_token'], keys)
        
        if not key_data:
            print(f"⚠️  Batch {batch_id}/{total_batches}: No data found")
            return {}
        
        print(f"✅ Batch {batch_id}/{total_batches}: Read {len(key_data)} keys")
        return key_data
        
    except Exception as e:
        print(f"❌ Batch {batch_id}/{total_batches} failed: {e}")
        return {}


# -------------------------------
# Main export function
# -------------------------------
def export_to_json():
    config = get_config()
    
    # Validate config
    if not config.get('src_url') or not config.get('src_token'):
        print("❌ Missing required environment variables!")
        print("   Please set: SRC_REDIS_REST_URL, SRC_REDIS_REST_TOKEN")
        return
    
    print("="*60)
    print("📥 EXPORTING REDIS DATABASE TO JSON")
    print("="*60)
    
    # Step 1: Scan all keys
    all_keys = scan_all_keys(config['src_url'], config['src_token'])
    
    if not all_keys:
        print("⚠️  No keys found to export")
        return
    
    # Step 2: Split into batches
    batches = [all_keys[i:i + BATCH_SIZE] for i in range(0, len(all_keys), BATCH_SIZE)]
    total_batches = len(batches)
    
    print(f"\n📦 Created {total_batches} batches of up to {BATCH_SIZE} keys each")
    print(f"🧵 Using {THREADS} threads for parallel reading")
    print(f"\n{'='*60}")
    print("⚡ Starting data export...\n")
    
    # Step 3: Read all data with threading
    all_data = {}
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        
        for i, batch in enumerate(batches, 1):
            future = executor.submit(read_batch, config, batch, i, total_batches)
            futures.append(future)
        
        # Wait for all batches to complete
        for future in as_completed(futures):
            batch_data = future.result()
            all_data.update(batch_data)
    
    # Step 4: Create output directory if needed
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Step 5: Write to JSON file
    print(f"\n{'='*60}")
    print(f"💾 Writing data to {OUTPUT_FILE}...")
    
    output = {
        "metadata": {
            "total_keys": len(all_data),
            "source_url": config['src_url'],
            "export_timestamp": None  # Could add timestamp if needed
        },
        "keys": all_data
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"{'='*60}")
    print(f"✅ EXPORT COMPLETE!")
    print(f"{'='*60}")
    print(f"📊 Total keys exported: {len(all_data):,}")
    print(f"📁 Output file: {OUTPUT_FILE}")
    print(f"💾 File size: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.2f} MB")
    print(f"{'='*60}\n")


# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    export_to_json()