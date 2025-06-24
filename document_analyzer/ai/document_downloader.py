from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin, urlparse
import os
import requests
from document_analyzer.gcp.gcs_client import GCSClient

class DocumentDownloader:
    """
    Downloads all document files from a given URL and uploads them to a GCS bucket.
    Uses Selenium to handle dynamically rendered content, searching in <a>, <iframe>, and <embed> tags.
    """

    def __init__(self, gcs_client: GCSClient):
        """
        Initializes the DocumentDownloader with a GCS client.

        Args:
            gcs_client (GCSClient): An instance of the GCSClient class.
        """
        self.gcs_client = gcs_client

    def get_document_links(self, url: str, a_class: str = None):
        """
        Uses Selenium to extract document links from a dynamically rendered web page.
        Searches in <a>, <iframe>, and <embed> tags. Detects documents by:
        - File extension in href
        - type attribute (e.g., "application/pdf")
        - class names containing document types
        """
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome()
        driver.get(url)

        # Document types to look for (both extensions and MIME types)
        doc_extensions = [".pdf", ".docx", ".doc", ".pptx", ".xlsx"]
        doc_types = ["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx"]
        doc_links = []  # Changed to list to store tuples (url, extension)

        # <a> tags
        if a_class:
            links = driver.find_elements(By.CSS_SELECTOR, f"a.{a_class}")
        else:
            links = driver.find_elements(By.TAG_NAME, "a")
        
        for link in links:
            href = link.get_attribute("href")
            if not href:
                continue
                
            # Check by file extension
            if any(ext in href.lower() for ext in doc_extensions):
                doc_links.append((urljoin(url, href), None))
                continue
                
            # Check by type attribute and determine extension if needed
            link_type = link.get_attribute("type")
            if link_type:
                for doc_type in doc_types:
                    if doc_type in link_type.lower():
                        # Determine extension if not present
                        extension = None
                        if not any(ext in href.lower() for ext in doc_extensions):
                            if doc_type == "pdf":
                                extension = ".pdf"
                            elif doc_type == "doc":
                                extension = ".doc"
                            elif doc_type == "docx":
                                extension = ".docx"
                            elif doc_type in ["ppt", "pptx"]:
                                extension = ".pptx"
                            elif doc_type in ["xls", "xlsx"]:
                                extension = ".xlsx"
                        doc_links.append((urljoin(url, href), extension))
                        break
                continue
                
            # Check by class attribute and determine extension if needed
            link_class = link.get_attribute("class")
            if link_class:
                for doc_type in doc_types:
                    if doc_type in link_class.lower():
                        # Determine extension if not present
                        extension = None
                        if not any(ext in href.lower() for ext in doc_extensions):
                            if doc_type == "pdf":
                                extension = ".pdf"
                            elif doc_type == "doc":
                                extension = ".doc"
                            elif doc_type == "docx":
                                extension = ".docx"
                            elif doc_type in ["ppt", "pptx"]:
                                extension = ".pptx"
                            elif doc_type in ["xls", "xlsx"]:
                                extension = ".xlsx"
                        doc_links.append((urljoin(url, href), extension))
                        break
                continue

        # <iframe> tags (similar logic)
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if not src:
                continue
                
            if any(ext in src.lower() for ext in doc_extensions):
                doc_links.append((urljoin(url, src), None))
                continue
                
            iframe_type = iframe.get_attribute("type")
            if iframe_type:
                for doc_type in doc_types:
                    if doc_type in iframe_type.lower():
                        extension = None
                        if not any(ext in src.lower() for ext in doc_extensions):
                            if doc_type == "pdf":
                                extension = ".pdf"
                            elif doc_type == "doc":
                                extension = ".doc"
                            elif doc_type == "docx":
                                extension = ".docx"
                            elif doc_type in ["ppt", "pptx"]:
                                extension = ".pptx"
                            elif doc_type in ["xls", "xlsx"]:
                                extension = ".xlsx"
                        doc_links.append((urljoin(url, src), extension))
                        break
                continue

        # <embed> tags (similar logic)
        embeds = driver.find_elements(By.TAG_NAME, "embed")
        for embed in embeds:
            src = embed.get_attribute("src")
            if not src:
                continue
                
            if any(ext in src.lower() for ext in doc_extensions):
                doc_links.append((urljoin(url, src), None))
                continue
                
            embed_type = embed.get_attribute("type")
            if embed_type:
                for doc_type in doc_types:
                    if doc_type in embed_type.lower():
                        extension = None
                        if not any(ext in src.lower() for ext in doc_extensions):
                            if doc_type == "pdf":
                                extension = ".pdf"
                            elif doc_type == "doc":
                                extension = ".doc"
                            elif doc_type == "docx":
                                extension = ".docx"
                            elif doc_type in ["ppt", "pptx"]:
                                extension = ".pptx"
                            elif doc_type in ["xls", "xlsx"]:
                                extension = ".xlsx"
                        doc_links.append((urljoin(url, src), extension))
                        break
                continue

        driver.quit()
        return doc_links

    def download_file(self, file_url: str, dest_folder: str = "downloads", extension: str = None):
        """
        Downloads a file from a URL to a local folder.

        Args:
            file_url (str): The URL of the file to download.
            dest_folder (str): The local folder to save the file.
            extension (str, optional): Extension to add to the filename if not present.

        Returns:
            str: The local file path.
        """
        os.makedirs(dest_folder, exist_ok=True)
        local_filename = os.path.basename(urlparse(file_url).path)
        
        # Add extension if provided and not already present
        if extension and not any(local_filename.lower().endswith(ext) for ext in [".pdf", ".docx", ".doc", ".pptx", ".xlsx"]):
            local_filename += extension
            
        local_path = os.path.join(dest_folder, local_filename)
        
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_path

    def process_url(self, url: str, gcs_folder: str = "", a_class: str = None):
        """
        Downloads all documents from the given URL and uploads them to GCS.

        Args:
            url (str): The URL to process.
            gcs_folder (str): The folder in the GCS bucket to upload files to.
            a_class (str, optional): If provided, only <a> tags with this class will be considered.
        """
        doc_links = self.get_document_links(url, a_class=a_class)
        print(f"Found {len(doc_links)} document(s) at {url}")
        for doc_url, extension in doc_links:
            try:
                print(f"Downloading {doc_url} ...")
                local_path = self.download_file(doc_url, extension=extension)
                destination_blob = os.path.join(gcs_folder, os.path.basename(local_path)) if gcs_folder else os.path.basename(local_path)
                destination_blob=  destination_blob.replace("\\","/")
                print(f"Uploading {local_path} to GCS as {destination_blob} ...")
                self.gcs_client.upload_blob(local_path, destination_blob)
                os.remove(local_path)
            except Exception as e:
                print(e)
        print("All documents processed and uploaded.") 