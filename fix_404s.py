import os
import sys
import urllib.parse
from bs4 import BeautifulSoup
import chardet

# Configuration
ROOT_DIR = os.getcwd()
EXTENSIONS_TO_CHECK = ['.html', '.htm', '.js', '.css']
DRY_RUN = True  # Default to dry run for safety

def get_files_in_directory(directory):
    """Returns a dictionary of {lowercase_name: actual_name} for a directory."""
    try:
        files = os.listdir(directory)
        return {f.lower(): f for f in files}
    except OSError:
        return {}

def resolve_path(file_path, link_url):
    """
    Resolves a link URL relative to the file_path.
    Returns:
        absolute_file_path (or None if external),
        is_absolute_url (bool)
    """
    # Ignore external links, anchors, mailto, etc.
    if link_url.startswith(('http:', 'https:', 'mailto:', 'tel:', '#', 'javascript:', 'data:')):
        return None, False

    # Decode URL (e.g. %20 -> space)
    link_url = urllib.parse.unquote(link_url)
    
    # Strip query params and fragments
    link_url = link_url.split('?')[0].split('#')[0]

    if not link_url:
        return None, False

    if link_url.startswith('/'):
        # Root relative
        # Assuming ROOT_DIR is the web root
        abs_path = os.path.join(ROOT_DIR, link_url.lstrip('/'))
        return abs_path, True
    else:
        # Relative to current file
        dir_name = os.path.dirname(file_path)
        abs_path = os.path.join(dir_name, link_url)
        return abs_path, False

def check_and_fix_file(file_path, dry_run=True):
    """Checks links in a file and proposes/applies fixes."""
    try:
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw = f.read()
            encoding = chardet.detect(raw)['encoding'] or 'utf-8'
        
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"[!] Could not read {file_path}: {e}")
        return 0

    soup = BeautifulSoup(content, 'html.parser')
    modified = False
    issues_found = 0

    # Elements to check
    tags = {
        'a': 'href',
        'link': 'href',
        'script': 'src',
        'img': 'src',
        'source': 'src',
        'iframe': 'src',
        'meta': 'content' # Sometimes used for redirects or images
    }

    for tag_name, attr in tags.items():
        for tag in soup.find_all(tag_name):
            url = tag.get(attr)
            if not url:
                continue
            
            # Special case for meta tags that aren't URLs
            if tag_name == 'meta':
                # Only check common URL attributes in meta
                if tag.get('property') not in ['og:image', 'og:url', 'twitter:image']:
                    continue

            target_path, is_root_relative = resolve_path(file_path, url)
            
            if not target_path:
                continue

            # Check if file exists
            if os.path.exists(target_path) and os.path.isfile(target_path):
                continue
            
            # If directory, check for index.html
            if os.path.isdir(target_path):
                 if os.path.exists(os.path.join(target_path, 'index.html')):
                     continue

            # ISSUE FOUND
            issues_found += 1
            print(f"[-] Broken Link in {os.path.basename(file_path)}: {url}")
            
            # Attempt FIX: Case Insensitivity
            target_dir = os.path.dirname(target_path)
            target_file = os.path.basename(target_path)
            
            if os.path.exists(target_dir):
                files_map = get_files_in_directory(target_dir)
                if target_file.lower() in files_map:
                    real_name = files_map[target_file.lower()]
                    print(f"    [+] Fix Available: Case mismatch. Change '{target_file}' to '{real_name}'")
                    
                    if not dry_run:
                        # Construct new URL
                        new_url = url.replace(target_file, real_name)
                        tag[attr] = new_url
                        modified = True
                        print(f"    [!] FIXED: Updated to {new_url}")
                else:
                    print(f"    [?] File not found in directory. No automatic fix.")
            else:
                print(f"    [?] Directory does not exist: {target_dir}")

    if modified and not dry_run:
        try:
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(str(soup))
            print(f"[SUCCESS] Saved changes to {file_path}")
        except Exception as e:
            print(f"[!] Failed to write {file_path}: {e}")

    return issues_found

def main():
    global DRY_RUN
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        DRY_RUN = False
        print("MATCH MODE: FIXING ERRORS")
    else:
        print("MATCH MODE: DRY RUN (No changes will be made)")
        print("Run with '--fix' to apply changes.")

    total_issues = 0
    checked_files = 0

    for root, dirs, files in os.walk(ROOT_DIR):
        # Skip hidden folders and backups
        if '.git' in root or 'deploy_backups' in root:
            continue
            
        for file in files:
            if any(file.endswith(ext) for ext in EXTENSIONS_TO_CHECK):
                file_path = os.path.join(root, file)
                # Skip the mirror script itself and report logs
                if file in ['fix_404s.py', 'mirror_log.txt']:
                    continue
                    
                total_issues += check_and_fix_file(file_path, DRY_RUN)
                checked_files += 1

    print("\n" + "="*40)
    print(f"Scan Complete.")
    print(f"Files Checked: {checked_files}")
    print(f"Broken Links Found: {total_issues}")
    if DRY_RUN and total_issues > 0:
        print("Run 'python fix_404s.py --fix' to apply automatic repairs.")

if __name__ == "__main__":
    main()
