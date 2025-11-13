# VCBench Docker Configuration

This directory contains Docker configurations for running bioinformatics tools and databases required by VCBench.

## Files

- `compose.yaml` - Main Docker Compose configuration (AMD64)
- `docker-compose.arm64.yaml` - ARM64-specific configuration for M1/M2/M3 Macs
- `docker-troubleshoot.sh` - Diagnostic script for Docker issues
- `Dockerfile.rtg` - Dockerfile for RTG Tools
- `db_start.sh` - Database initialization script

## Services

### rtg
**RTG Tools** - For variant analysis and benchmarking
- Built from local `Dockerfile.rtg`
- Requires significant memory (8GB limit)

### happy
**hap.py** - Small variant benchmarking tool
- Pre-built image: `pkrusche/hap.py:latest`
- Requires high memory (48GB limit)

### bcftools
**BCFtools** - VCF/BCF manipulation utilities
- Image: `quay.io/biocontainers/bcftools:1.18--h8b37899_0`
- Lightweight utility container

### multiqc
**MultiQC** - Quality control report aggregation
- Image: `multiqc/multiqc:v1.19`
- Generates comprehensive QC reports

### db
**PostgreSQL** - Database for storing analysis results
- Image: `postgres:16-alpine`
- Persistent data storage with health checks

## Common Issues and Solutions

### ❌ "pull access denied" Errors

**Problem**: Docker cannot pull some images because they don't exist or require authentication.

**Solution**:
```bash
# Use the corrected compose files provided
docker compose up -d

# Or manually pull working images
docker pull quay.io/biocontainers/bcftools:1.18--h8b37899_0
docker pull postgres:16-alpine
docker pull multiqc/multiqc:v1.19
docker pull pkrusche/hap.py:latest
```

### ❌ "no matching manifest for linux/arm64" Errors

**Problem**: You're on an M1/M2/M3 Mac (ARM64) and some images don't support this architecture.

**Solutions**:

1. **Enable Rosetta in Docker Desktop** (Recommended):
   - Open Docker Desktop
   - Go to Settings → General
   - Check "Use Rosetta for x86/amd64 emulation on Apple Silicon"
   - Restart Docker Desktop

2. **Use ARM64-specific compose file**:
   ```bash
   docker compose -f docker-compose.arm64.yaml up -d
   ```

3. **Use the diagnostic script**:
   ```bash
   ./docker-troubleshoot.sh
   ```

### ❌ Memory Issues

**Problem**: Containers require more memory than allocated.

**Solution**:
- Increase Docker Desktop memory limit to at least 8GB (16GB recommended)
- Docker Desktop → Settings → Resources → Memory

### ❌ Port Conflicts

**Problem**: Port 5432 already in use.

**Solution**:
```bash
# Check what's using port 5432
lsof -i :5432

# Kill the process or change port in compose.yaml
# ports:
#   - "5433:5432"  # Use host port 5433
```

## Usage

### Start All Services
```bash
# Standard (AMD64)
docker compose up -d

# ARM64 Macs
docker compose -f docker-compose.arm64.yaml up -d
```

### Check Service Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f db
```

### Stop Services
```bash
docker compose down
```

### Clean Up
```bash
# Stop and remove containers/volumes
docker compose down -v

# Remove all unused images
docker system prune -a
```

## Diagnostic Script

Run the troubleshooting script for automated diagnosis:
```bash
./docker-troubleshoot.sh
```

This script will:
- ✅ Check Docker installation and versions
- ✅ Detect system architecture (ARM64/AMD64)
- ✅ Test basic Docker functionality
- ✅ Attempt to start services with appropriate configuration
- ✅ Provide specific solutions for your system

## Architecture-Specific Notes

### Intel/AMD64 Systems
- Use `compose.yaml` (default)
- All services should work without issues
- Native performance

### Apple Silicon (M1/M2/M3) Macs
- **Option 1**: Enable Rosetta emulation in Docker Desktop
- **Option 2**: Use `docker-compose.arm64.yaml` for native ARM64 images
- **Option 3**: Run diagnostic script for automatic detection

## Volume Management

Data is persisted in named volumes:
- `db-data` - PostgreSQL database files

To completely reset the database:
```bash
docker compose down -v
docker compose up -d db
```

## Building Custom Images

### RTG Tools
```bash
docker build -f Dockerfile.rtg -t rtg-tools .
```

### hap.py (if needed)
The hap.py service uses a pre-built image. To build locally:
```bash
# This would require the hap.py source code
# docker build -t happy ../tools/hap.py
```

## Security Notes

- Database credentials are set for development only
- Change passwords in production
- Use Docker secrets for sensitive data
- Consider using private registries for custom images

## Performance Tuning

### Memory Limits
- RTG Tools: 8GB (configurable via RTG_MEM=6g)
- hap.py: 48GB (configurable via RTG_MEM=24g)
- PostgreSQL: No specific limit (uses Alpine base)

### CPU Usage
Some bioinformatics tools are CPU-intensive. Consider:
- Increasing CPU allocation in Docker Desktop
- Using `--cpus` parameter in compose files
- Running computationally intensive tasks during off-peak hours

## Troubleshooting Checklist

1. ✅ Docker Desktop is running
2. ✅ Sufficient memory allocated (≥8GB)
3. ✅ Correct architecture configuration
4. ✅ No port conflicts
5. ✅ Internet connection for image pulls
6. ✅ Sufficient disk space
7. ✅ Docker Desktop is up to date

If issues persist, run the diagnostic script and check the logs.
