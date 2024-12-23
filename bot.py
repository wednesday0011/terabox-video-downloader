async def get_terabox_info(url):
    """Extract necessary info from TeraBox link."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }
    
    # Convert 1024terabox.com to www.terabox.com
    url = url.replace('1024terabox.com', 'www.terabox.com')
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                if response.status != 200:
                    print(f"Failed to fetch page: {response.status}")
                    print(f"Response headers: {response.headers}")
                    return None
                
                html = await response.text()
                print(f"Page length: {len(html)}")  # Debug print
                
                # Try to find the share_id from URL if it's not in the standard format
                share_id = None
                if 's/' in url:
                    share_id = url.split('s/')[1].split('?')[0]
                    print(f"Extracted share_id from URL: {share_id}")
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # First try to find the data in window.__INITIAL_STATE__
                scripts = soup.find_all('script')
                initial_state = None
                
                for script in scripts:
                    if not script.string:
                        continue
                        
                    # Debug print each script
                    script_text = script.string.strip()
                    print(f"Found script of length: {len(script_text)}")
                    
                    if 'window.__INITIAL_STATE__' in script_text:
                        print("Found __INITIAL_STATE__ script!")
                        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', script_text)
                        if match:
                            try:
                                initial_state = json.loads(match.group(1))
                                break
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error: {e}")
                                continue
                
                if initial_state:
                    try:
                        file_info = initial_state['file']['list'][0]
                        return {
                            'fs_id': file_info['fs_id'],
                            'share_id': initial_state['file']['share_id'],
                            'sign': initial_state['file']['sign'],
                            'timestamp': initial_state['file']['timestamp'],
                            'filename': file_info['filename']
                        }
                    except (KeyError, IndexError) as e:
                        print(f"Error extracting info from initial_state: {e}")
                        
                # Fallback: Try to find data in other script tags
                for script in scripts:
                    if not script.string:
                        continue
                    
                    script_text = script.string.strip()
                    
                    # Look for file list data
                    if 'fileList' in script_text:
                        try:
                            file_list_match = re.search(r'fileList\s*=\s*(\[.+?\]);', script_text)
                            if file_list_match:
                                file_list = json.loads(file_list_match.group(1))
                                sign_match = re.search(r'sign\s*=\s*[\'"](.+?)[\'"]', script_text)
                                timestamp_match = re.search(r'timestamp\s*=\s*[\'"]?(\d+)[\'"]?', script_text)
                                
                                if file_list and sign_match and timestamp_match:
                                    return {
                                        'fs_id': file_list[0]['fs_id'],
                                        'share_id': share_id,
                                        'sign': sign_match.group(1),
                                        'timestamp': timestamp_match.group(1),
                                        'filename': file_list[0]['server_filename']
                                    }
                        except Exception as e:
                            print(f"Error in fallback extraction: {e}")
                
                print("Could not find required data in any script tag")
                return None
                
        except Exception as e:
            print(f"Error getting TeraBox info: {e}")
            return None
