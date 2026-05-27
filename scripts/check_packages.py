import sys
packages = ['pandas', 'openpyxl', 'geojson', 'newick', 'xlrd', 'odf']
for p in packages:
    try:
        __import__(p)
        print(f"{p}: installed")
    except ImportError:
        print(f"{p}: MISSING")
