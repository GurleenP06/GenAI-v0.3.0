"""Main document processor orchestrating OPMP/IMP processing, chunking, and vector DB creation."""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple

import pandas as pd
from sentence_transformers import SentenceTransformer

from oskar.config import EMBEDDING_MODEL_PATH, DEVICE, TXT_DIRECTORY
from oskar.extraction import extract_text
from oskar.pipeline.opmp_processor import OPMPProcessor
from oskar.pipeline.imp_processor import IMPProcessor
from oskar.pipeline.chunking import create_chunks
from oskar.pipeline.vectordb import create_vector_database

logger = logging.getLogger(__name__)


class DocumentProcessor:

    SUPPORTED_FORMATS = (".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".xlsm")
    SKIP_FILES = ["sourcelinks.xlsx", "sourcelinks.txt"]

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        batch_size: int = 32
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size

        self.text_output_dir = self.output_dir / "Text"
        self.text_output_dir.mkdir(parents=True, exist_ok=True)

        self.opmp_processor = OPMPProcessor()
        self.imp_processor = IMPProcessor()

        print(f"Loading embedding model: {EMBEDDING_MODEL_PATH}")
        self.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_PATH,
            device=DEVICE
        )

        self.metadata_path = self.output_dir / "metadata.csv"
        self.faiss_index_path = self.output_dir / "faiss_index"
        self.acronyms_path = self.output_dir / "document_acronyms.json"
        self.references_path = self.output_dir / "document_references.json"
        self.source_links_path = self.input_dir / "SourceLinks.xlsx"

    def load_source_links(self) -> Dict[str, str]:
        if not self.source_links_path.exists():
            return {}
        try:
            df = pd.read_excel(self.source_links_path)
            return dict(zip(df['File Name'], df['Original URL']))
        except Exception as e:
            logger.error(f"Error loading source links: {e}")
            return {}

    def _create_chunks(self, text: str) -> List[str]:
        return create_chunks(text, self.chunk_size, self.chunk_overlap)

    def should_skip_file(self, filename: str) -> bool:
        return filename.lower() in [f.lower() for f in self.SKIP_FILES]

    def _extract_text(self, file_path: Path) -> str:
        return extract_text(file_path)

    def process_documents(self) -> Tuple[List[Dict], Dict]:
        print("\n" + "=" * 60)
        print("DOCUMENT PROCESSING")
        print("=" * 60)

        source_url_mapping = self.load_source_links()

        files_to_process = []
        for root, _, files in os.walk(self.input_dir):
            if Path(root).name == "Text":
                continue
            for file in files:
                if self.should_skip_file(file):
                    continue
                if file.lower().endswith(self.SUPPORTED_FORMATS):
                    files_to_process.append(Path(root) / file)

        print(f"Found {len(files_to_process)} documents to process")

        all_acronyms = {}
        all_references = {}
        all_chunks_metadata = []
        processed_count = 0
        opmp_count = 0
        imp_count = 0

        for file_path in files_to_process:
            filename_upper = file_path.name.upper()
            source_url = source_url_mapping.get(file_path.name, "")

            if filename_upper.startswith('OPMP') and file_path.suffix.lower() == '.pdf':
                result = self.opmp_processor.process(file_path, source_url)

                if result:
                    text_file_path = self.text_output_dir / result["filename"]
                    with open(text_file_path, 'w', encoding='utf-8') as f:
                        f.write(result["clean_text"])

                    if result["acronyms"]:
                        all_acronyms[result["filename"]] = result["acronyms"]
                    if result["references"]:
                        all_references[result["filename"]] = result["references"]

                    chunks = self._create_chunks(result["clean_text"])
                    for chunk in chunks:
                        all_chunks_metadata.append({
                            "chunk_text": chunk,
                            "filename": result["filename"],
                            "source_url": source_url,
                            "document_type": "OPMP",
                            "opmp_number": result["metadata"]["opmp_number"],
                            "revision": result["metadata"]["revision_number"],
                            "procedure_title": result["metadata"]["procedure_title"]
                        })

                    processed_count += 1
                    opmp_count += 1

            elif filename_upper.startswith('IMP') and file_path.suffix.lower() == '.pdf':
                result = self.imp_processor.process(file_path, source_url)

                if result:
                    text_file_path = self.text_output_dir / result["filename"]
                    with open(text_file_path, 'w', encoding='utf-8') as f:
                        f.write(result["clean_text"])

                    if result["acronyms"]:
                        all_acronyms[result["filename"]] = result["acronyms"]
                    if result["references"]:
                        all_references[result["filename"]] = result["references"]

                    chunks = self._create_chunks(result["clean_text"])
                    for chunk in chunks:
                        all_chunks_metadata.append({
                            "chunk_text": chunk,
                            "filename": result["filename"],
                            "source_url": source_url,
                            "document_type": "IMP",
                            "imp_number": result["metadata"]["imp_number"],
                            "revision": result["metadata"]["revision_number"],
                            "procedure_title": result["metadata"]["procedure_title"]
                        })

                    processed_count += 1
                    imp_count += 1

            else:
                text = self._extract_text(file_path)
                if text:
                    text_filename = file_path.stem + ".txt"
                    text_file_path = self.text_output_dir / text_filename
                    with open(text_file_path, 'w', encoding='utf-8') as f:
                        f.write(text)

                    chunks = self._create_chunks(text)
                    for chunk in chunks:
                        all_chunks_metadata.append({
                            "chunk_text": chunk,
                            "filename": text_filename,
                            "source_url": source_url,
                            "document_type": "General"
                        })

                    processed_count += 1

            print(f"\rProcessed {processed_count}/{len(files_to_process)} files...", end='', flush=True)

        print()

        with open(self.acronyms_path, 'w', encoding='utf-8') as f:
            json.dump(all_acronyms, f, indent=2)

        with open(self.references_path, 'w', encoding='utf-8') as f:
            json.dump(all_references, f, indent=2)

        print(f"\nProcessed: {processed_count} documents ({opmp_count} OPMPs, {imp_count} IMPs)")
        print(f"Total chunks: {len(all_chunks_metadata)}")

        return all_chunks_metadata, {"acronyms": all_acronyms, "references": all_references}

    def run_pipeline(self):
        print("\n" + "=" * 60)
        print("DOCUMENT PROCESSING PIPELINE")
        print("=" * 60)
        print(f"Input: {self.input_dir}")
        print(f"Output: {self.output_dir}")
        print(f"Chunk size: {self.chunk_size}, Overlap: {self.chunk_overlap}")

        chunks_metadata, knowledge = self.process_documents()

        if not chunks_metadata:
            print("No documents processed")
            return

        create_vector_database(
            chunks_metadata,
            str(self.faiss_index_path),
            str(self.metadata_path),
            self.embedding_model,
            self.batch_size
        )

        print("\n" + "=" * 60)
        print("COMPLETE")
        print("=" * 60)


def main():
    processor = DocumentProcessor(
        input_dir=TXT_DIRECTORY,
        output_dir=".",
        chunk_size=512,
        chunk_overlap=64,
        batch_size=32
    )
    processor.run_pipeline()


if __name__ == "__main__":
    main()
