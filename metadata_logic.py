import os
import re
import shutil
import zipfile
import logging
import io
import xml.etree.ElementTree as ET

def _strip_namespace_from_xml(xml_content):
    """
    Parses XML content and removes all namespace prefixes and URIs.
    This simplifies parsing for XML files from various sources.
    """
    it = ET.iterparse(io.BytesIO(xml_content))
    for _, el in it:
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
        for name in list(el.attrib):
            if '}' in name:
                new_name = name.split('}', 1)[1]
                el.attrib[new_name] = el.attrib.pop(name)
    return it.root

def parse_comic_filename(filename):
    """
    Parses a .cbz filename to get series, issue, and volume.
    Tries multiple specific patterns first before falling back to general ones.
    """
    # Pattern 1: Handles "SP" year annuals
    match = re.match(r'^(.*?)\s+v(\d+)\s+SP(\d{4})(?:\s+\(\d{4}\))?\s*\.cbz$', filename, re.IGNORECASE)
    if match:
        series = match.group(1).strip()
        volume = match.group(2)
        issue_number = f"Annual {match.group(3)}"
        return series, issue_number, volume

    # Pattern 2: Handles standard, decimal, and dot-letter issues
    match = re.match(r'^(.*?)\s+v(\d+)\s+(.*?)\s*(\d+(\.\w+)?)(?:\s+\(\d{4}\))?\s*\.cbz$', filename, re.IGNORECASE)
    if match:
        series = f"{match.group(1).strip()} {match.group(3).strip()}".strip()
        volume = match.group(2)
        issue_number = match.group(4)
        return series, issue_number, volume

    # Pattern 3: Fallback for files with no volume tag
    match = re.match(r'^(.*?)\s+(\d+(\.\w+)?)(?:\s+\(of\s+\d+\))?(?:\s+\(\d{4}\))?\s*\.cbz$', filename, re.IGNORECASE)
    if match:
        series = match.group(1).strip()
        issue_number = match.group(2)
        return series, issue_number, "1" # Assume Volume 1

    return None, None, None

def _update_or_create_tag(root, tag_name, value):
    """Helper function to find a tag and update its text, or create it if it doesn't exist."""
    elem = root.find(tag_name)
    if elem is None:
        elem = ET.SubElement(root, tag_name)
    elem.text = str(value)

def process_comic_metadata(cbz_path, mode):
    """
    Efficiently processes a CBZ file to add/update or remove ComicInfo.xml.
    """
    filename = os.path.basename(cbz_path)
    temp_cbz_path = cbz_path + '.tmp'
    
    try:
        xml_found_in_source = False
        with zipfile.ZipFile(cbz_path, 'r') as source_zip:
            if mode == 'update':
                series, issue_number, volume = parse_comic_filename(filename)
                if not all([series, issue_number, volume]):
                    return 'FAILURE_PARSE', f"Filename format not recognized or is set to be ignored."

                try:
                    xml_content = source_zip.read('ComicInfo.xml')
                    root = _strip_namespace_from_xml(xml_content) 
                    xml_found_in_source = True
                except KeyError:
                    root = ET.Element('ComicInfo')
                    xml_found_in_source = False

                # --- MODIFIED LOGIC BLOCK FOR <Number> TAG ---

                # 1. Determine the value for the <Number> tag.
                number_for_tag = issue_number
                if '.' in issue_number:
                    parts = issue_number.split('.', 1)
                    # Check if the part after the dot consists ONLY of letters.
                    if len(parts) > 1 and parts[1].isalpha():
                        # If so, replace the letter suffix with '.1'
                        # Example: '54.LR' becomes '54.1'
                        number_for_tag = f"{parts[0]}.1"
                
                # 2. Determine the full, descriptive value for the <Title> tag.
                # This always uses the original, full issue_number.
                number_for_title = issue_number
                
                # 3. Handle Annuals as a special case for both tags.
                if issue_number.lower().startswith('annual'):
                    number_for_tag = issue_number
                    number_for_title = issue_number
                    formatted_title = f"{series} v{volume} {number_for_title}"
                else:
                    # Clean up leading zeros for a nicer display in the title.
                    number_for_title = number_for_title.lstrip('0')
                    if number_for_title.startswith('.'): number_for_title = '0' + number_for_title
                    if not number_for_title and len(issue_number) > 0: number_for_title = '0'
                    
                    formatted_title = f"{series} v{volume} #{number_for_title}"

                # 4. Clean up the final <Number> tag value (strip leading zeros).
                number_for_tag = number_for_tag.lstrip('0')
                if number_for_tag.startswith('.'): number_for_tag = '0' + number_for_tag
                if not number_for_tag and len(issue_number) > 0: number_for_tag = '0'
                
                # 5. Create/Update the XML tags with the correct values.
                _update_or_create_tag(root, 'Series', series)
                _update_or_create_tag(root, 'Volume', volume)
                _update_or_create_tag(root, 'Number', number_for_tag)
                _update_or_create_tag(root, 'Title', formatted_title)
                
                updated_xml_bytes = ET.tostring(root, encoding='utf-8', xml_declaration=True)

            with zipfile.ZipFile(temp_cbz_path, 'w', zipfile.ZIP_DEFLATED) as target_zip:
                for item in source_zip.infolist():
                    if item.filename.lower() == 'comicinfo.xml':
                        continue
                    target_zip.writestr(item, source_zip.read(item.filename))
                
                if mode == 'update':
                    target_zip.writestr('ComicInfo.xml', updated_xml_bytes)

        shutil.move(temp_cbz_path, cbz_path)
        
        if mode == 'update':
            message = "Updated existing ComicInfo.xml." if xml_found_in_source else "Created new ComicInfo.xml."
            status = 'SUCCESS_UPDATED' if xml_found_in_source else 'SUCCESS_CREATED'
            return status, message
        elif mode == 'remove':
            xml_in_source = any(f.lower() == 'comicinfo.xml' for f in source_zip.namelist())
            if xml_in_source:
                return 'SUCCESS_REMOVED', "ComicInfo.xml was removed."
            else:
                return 'SKIPPED_NO_XML', "No ComicInfo.xml found to remove."

    except Exception as e:
        return 'FAILURE_EXCEPTION', f"An unexpected error occurred: {e}"
    
    finally:
        if os.path.exists(temp_cbz_path):
            try:
                os.remove(temp_cbz_path)
            except OSError as e:
                logging.error(f"Failed to remove temp file {temp_cbz_path}: {e}")
                
    return 'FAILURE_UNKNOWN', "An unknown error occurred."