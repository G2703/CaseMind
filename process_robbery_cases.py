#!/usr/bin/env python3
"""
Script to process all robbery cases from High Court directory
Processes files in batches to avoid overwhelming the system
"""

import os
import sys
import time
from pathlib import Path
import subprocess
import json

def get_pdf_files(directory):
    """Get all PDF files from the directory"""
    pdf_files = []
    for file in Path(directory).iterdir():
        if file.suffix.lower() == '.pdf':
            pdf_files.append(file)
    return sorted(pdf_files)

def get_processed_files():
    """Get list of already processed files"""
    extracted_dir = Path("cases/extracted")
    if not extracted_dir.exists():
        return set()
    
    processed = set()
    for file in extracted_dir.iterdir():
        if file.suffix == '.json' and file.name.endswith('_facts.json'):
            case_name = file.name.replace('_facts.json', '')
            processed.add(case_name)
    return processed

def process_single_file(pdf_path):
    """Process a single PDF file using the pipeline"""
    try:
        cmd = f'python src/main_pipeline.py "{pdf_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            print(f"✅ Successfully processed: {pdf_path.name}")
            return True
        else:
            print(f"❌ Failed to process: {pdf_path.name}")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout processing: {pdf_path.name}")
        return False
    except Exception as e:
        print(f"❌ Exception processing {pdf_path.name}: {str(e)}")
        return False

def main():
    # Directory containing the PDF files
    robbery_dir = Path("cases/input_files/Cases/Robbery/High court")
    
    if not robbery_dir.exists():
        print(f"❌ Directory not found: {robbery_dir}")
        sys.exit(1)
    
    # Get all PDF files and already processed files
    pdf_files = get_pdf_files(robbery_dir)
    processed_files = get_processed_files()
    
    print(f"📁 Found {len(pdf_files)} PDF files in {robbery_dir}")
    print(f"✅ Already processed: {len(processed_files)} files")
    
    # Filter out already processed files
    remaining_files = []
    for pdf_file in pdf_files:
        case_name = pdf_file.stem  # filename without extension
        if case_name not in processed_files:
            remaining_files.append(pdf_file)
    
    print(f"📋 Remaining files to process: {len(remaining_files)}")
    
    if not remaining_files:
        print("🎉 All files have already been processed!")
        return
    
    # Ask user for batch size
    print("\n🚀 Processing Options:")
    print("1. Process all remaining files (may take several hours)")
    print("2. Process in small batches (recommended)")
    print("3. Process specific number of files")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        files_to_process = remaining_files
        batch_size = len(remaining_files)
    elif choice == "2":
        batch_size = int(input("Enter batch size (recommended: 10-20): ") or "10")
        files_to_process = remaining_files[:batch_size]
    elif choice == "3":
        count = int(input("Enter number of files to process: "))
        files_to_process = remaining_files[:count]
        batch_size = count
    else:
        print("❌ Invalid choice")
        return
    
    print(f"\n🔄 Processing {len(files_to_process)} files...")
    
    # Process the files
    successful = 0
    failed = 0
    start_time = time.time()
    
    for i, pdf_file in enumerate(files_to_process, 1):
        print(f"\n[{i}/{len(files_to_process)}] Processing: {pdf_file.name}")
        
        if process_single_file(pdf_file):
            successful += 1
        else:
            failed += 1
        
        # Show progress
        elapsed = time.time() - start_time
        avg_time_per_file = elapsed / i
        remaining_time = avg_time_per_file * (len(files_to_process) - i)
        
        print(f"Progress: {i}/{len(files_to_process)} | Success: {successful} | Failed: {failed}")
        print(f"Elapsed: {elapsed/60:.1f}m | Estimated remaining: {remaining_time/60:.1f}m")
        
        # Small delay to avoid overwhelming the API
        time.sleep(2)
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\n🏁 Processing Complete!")
    print(f"✅ Successfully processed: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total time: {total_time/60:.1f} minutes")
    print(f"⚡ Average time per file: {total_time/len(files_to_process):.1f} seconds")
    
    # Show what's left
    total_processed = len(processed_files) + successful
    total_files = len(pdf_files)
    remaining = total_files - total_processed
    
    print(f"\n📊 Overall Progress:")
    print(f"Total files: {total_files}")
    print(f"Processed: {total_processed}")
    print(f"Remaining: {remaining}")
    print(f"Progress: {(total_processed/total_files)*100:.1f}%")

if __name__ == "__main__":
    main()