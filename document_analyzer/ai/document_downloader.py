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
        Searches in <a>, <iframe>, and <embed> tags. Optionally, only <a> tags with a specific class.

        Args:
            url (str): The URL of the web page to analyze.
            a_class (str, optional): If provided, only <a> tags with this class will be considered.

        Returns:
            list: A list of absolute URLs to document files.
        """
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome()
        driver.get(url)

        exts = [".pdf", ".docx", ".doc", ".pptx", ".xlsx"]
        doc_links = set()

        # <a> tags
        if a_class:
            links = driver.find_elements(By.CSS_SELECTOR, f"a.{a_class}")
        else:
            links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and any(ext in href.lower() for ext in exts):
                doc_links.add(urljoin(url, href))

        # <iframe> tags
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and any(ext in src.lower() for ext in exts):
                doc_links.add(urljoin(url, src))

        # <embed> tags
        embeds = driver.find_elements(By.TAG_NAME, "embed")
        for embed in embeds:
            src = embed.get_attribute("src")
            if src and any(ext in src.lower() for ext in exts):
                doc_links.add(urljoin(url, src))

        driver.quit()
        return list(doc_links)

    def download_file(self, file_url: str, dest_folder: str = "downloads"):
        """
        Downloads a file from a URL to a local folder.

        Args:
            file_url (str): The URL of the file to download.
            dest_folder (str): The local folder to save the file.

        Returns:
            str: The local file path.
        """
        os.makedirs(dest_folder, exist_ok=True)
        local_filename = os.path.join(dest_folder, os.path.basename(urlparse(file_url).path))
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename

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
        for doc_url in doc_links:
            print(f"Downloading {doc_url} ...")
            local_path = self.download_file(doc_url)
            destination_blob = os.path.join(gcs_folder, os.path.basename(local_path)) if gcs_folder else os.path.basename(local_path)
            destination_blob=  destination_blob.replace("\\","/")
            print(f"Uploading {local_path} to GCS as {destination_blob} ...")
            self.gcs_client.upload_blob(local_path, destination_blob)
            os.remove(local_path)
        print("All documents processed and uploaded.") 