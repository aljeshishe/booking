#!/bin/bash

# Download and unpack Booking.com sitemap files without temporary files

set -e
mkdir -p urls

echo "Downloading and extracting files..."

# List of URLs to download
urls=(
    "https://www.booking.com/sitembk-hotel-en-gb.0068.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0067.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0066.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0065.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0064.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0063.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0062.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0061.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0060.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0059.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0058.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0057.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0056.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0055.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0054.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0053.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0052.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0051.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0050.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0049.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0048.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0047.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0046.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0045.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0044.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0043.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0042.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0041.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0040.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0039.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0038.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0037.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0036.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0035.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0034.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0033.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0032.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0031.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0030.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0029.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0028.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0027.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0026.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0025.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0024.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0023.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0022.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0021.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0020.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0019.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0018.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0017.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0016.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0015.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0014.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0013.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0012.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0011.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0010.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0009.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0008.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0007.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0006.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0005.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0004.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0003.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0002.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0001.xml.gz"
    "https://www.booking.com/sitembk-hotel-en-gb.0000.xml.gz"
)

# Process each URL
for url in "${urls[@]}"; do
    # Extract filename from URL
    filename=$(basename "$url" .gz)
    
    # Skip if file already exists
    if [[ -f "urls/$filename" ]]; then
        echo "Skipping existing: $filename"
        continue
    fi
    
    echo "Processing: $filename"
    
    # Download and extract directly without temporary files
    if curl -fsSL "$url" | gunzip > "urls/$filename"; then
        echo "✓ Done: $filename"
    else
        echo "✗ Failed: $filename"
        rm -f "urls/$filename"  # Remove partial file
    fi
done

echo "Download completed!"