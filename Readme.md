# This Script is used to migrate the db one to another

# Step 1 : Run the below command

```
bash

pip install upstash-redis python-dotenv
```


# Upstash Redis Export Tool

A Python utility for efficiently exporting Redis data from Upstash to JSON format with support for both optimized and full backup modes.

## Features

- **Two Export Modes:**
  - **Optimized Mode**: Uses `MGET` for fast exports (~2K operations for 96K keys)
  - **Full Mode**: Uses `TYPE`, `DUMP`, and `PTTL` for complete backups (~288K operations for 96K keys)
- **Parallel Processing**: Multi-threaded batch processing for faster exports
- **Progress Tracking**: Real-time feedback on export progress
- **Configurable**: Adjustable batch sizes and thread counts
- **Error Handling**: Graceful error recovery with detailed logging

## Prerequisites

- Python 3.7+
- Upstash Redis database with REST API access
- Required packages: `requests`, `python-dotenv`

## Installation

```bash
pip install requests python-dotenv
```

## Configuration

Create a `.env` file in your project root:

```env
SRC_REDIS_REST_URL=https://your-database.upstash.io
SRC_REDIS_REST_TOKEN=your-token-here
```

## Usage

### Basic Export

```bash
python export_script.py
```

### Customization

Modify these constants at the top of the script:

```python
BATCH_SIZE = 500    # Keys per batch
THREADS = 6         # Parallel threads
OUTPUT_FILE = "scripts/upstash_dump.json"  # Output path
```

### Choosing Export Mode

```python
# Optimized mode (faster, strings only)
export_to_json(use_optimized=True)

# Full mode (complete backup with all data types)
export_to_json(use_optimized=False)
```

## Export Modes Comparison

### Optimized Mode (Recommended for Strings)

**Pros:**
- 66% fewer operations
- Significantly faster
- Lower costs
- Ideal for large datasets

**Cons:**
- Only works with STRING type keys
- Doesn't preserve TTL values
- Not suitable for complex data types (hashes, lists, sets, sorted sets)

**Read Operations per Key:** ~0.02 (1 MGET per 500 keys)

### Full Mode (Complete Backup)

**Pros:**
- Supports all Redis data types
- Preserves TTL values
- Complete data fidelity
- Suitable for restoration

**Cons:**
- 3x more operations
- Slower execution
- Higher costs

**Read Operations per Key:** 3 (TYPE + DUMP + PTTL)

## Read Call Estimates

For a database with **96,000 keys**:

### Optimized Mode
- **SCAN operations**: ~192 (500 keys per scan)
- **MGET operations**: ~192 (500 keys per batch)
- **Total read calls**: ~384

### Full Mode
- **SCAN operations**: ~192 (500 keys per scan)
- **TYPE operations**: 96,000 (1 per key)
- **DUMP operations**: 96,000 (1 per key)
- **PTTL operations**: 96,000 (1 per key)
- **Total read calls**: ~288,192

## Output Format

The exported JSON file contains:

```json
{
  "metadata": {
    "total_keys": 96000,
    "source_url": "https://your-database.upstash.io",
    "method": "optimized_mget"
  },
  "keys": {
    "key1": {
      "type": "string",
      "value": "data",
      "ttl": -1
    }
  }
}
```

### Optimized Mode Output
- `type`: Always "string"
- `value`: Raw string value
- `ttl`: Always -1 (not preserved)

### Full Mode Output
- `type`: Actual Redis type (string, hash, list, etc.)
- `dump`: RDB serialized value
- `ttl`: Time-to-live in milliseconds (-1 for no expiry)

## Performance Tips

- **Batch Size**: Increase for fewer operations, decrease for better error recovery
- **Thread Count**: Adjust based on your network and system capabilities
- **Network**: Ensure stable connection for large exports
- **Memory**: Monitor memory usage with large datasets

## Error Handling

The script includes:
- Connection timeout protection (60s for pipeline, 30s for scan)
- Graceful batch failure recovery
- Detailed error logging
- Empty batch detection

## Limitations

### Optimized Mode
- Only STRING keys supported
- TTL values not preserved
- Not suitable for restoration requiring exact data types

### Both Modes
- Large databases may take significant time
- Network interruptions can affect progress
- Upstash rate limits may apply

## Troubleshooting

**Slow Export:**
- Reduce `BATCH_SIZE` to 250-300
- Reduce `THREADS` to 3-4
- Check network latency

**Missing Keys:**
- Use Full Mode for non-string types
- Check Upstash access permissions
- Verify REST API token

**Memory Issues:**
- Reduce `BATCH_SIZE`
- Process in multiple runs using SCAN cursor

## License

MIT

## Contributing

Feel free to submit issues and enhancement requests!

***

**Note**: Always test with a small subset of data before running full exports. Monitor your Upstash usage to avoid unexpected costs.# migration
