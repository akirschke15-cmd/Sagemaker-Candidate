"""
Unit tests for resume parser module (resume_parser.py)

Tests file parsing, validation, and text extraction.
"""
import pytest
import io
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ats_app'))

import resume_parser


class TestFileValidation:
    """Test file validation functions"""

    def test_validate_file_size_accepts_small_file(self):
        """validate_file_size should accept files under the limit"""
        small_file = b"x" * (1024 * 1024)  # 1 MB
        result = resume_parser.validate_file_size(small_file, max_size_mb=10.0)

        assert result is None

    def test_validate_file_size_rejects_oversized_file(self):
        """validate_file_size should reject files over the limit"""
        large_file = b"x" * (11 * 1024 * 1024)  # 11 MB
        result = resume_parser.validate_file_size(large_file, max_size_mb=10.0)

        assert result is not None
        assert "too large" in result.lower()
        assert "11" in result  # Size should be in message

    def test_validate_file_size_accepts_exact_limit(self):
        """validate_file_size should accept file exactly at limit"""
        exact_file = b"x" * (10 * 1024 * 1024)  # Exactly 10 MB
        result = resume_parser.validate_file_size(exact_file, max_size_mb=10.0)

        assert result is None

    def test_validate_file_size_rejects_empty_file(self):
        """validate_file_size should reject empty file bytes"""
        empty_file = b""
        result = resume_parser.validate_file_size(empty_file, max_size_mb=10.0)

        assert result is not None
        assert "no file data" in result.lower()

    def test_validate_file_size_custom_limit(self):
        """validate_file_size should respect custom size limit"""
        file_2mb = b"x" * (2 * 1024 * 1024)  # 2 MB

        # Should pass with 5MB limit
        result = resume_parser.validate_file_size(file_2mb, max_size_mb=5.0)
        assert result is None

        # Should fail with 1MB limit
        result = resume_parser.validate_file_size(file_2mb, max_size_mb=1.0)
        assert result is not None


class TestTextCleaning:
    """Test text cleaning functions"""

    def test_clean_extracted_text_handles_empty_input(self):
        """clean_extracted_text should handle empty string"""
        result = resume_parser.clean_extracted_text("")
        assert result == ""

    def test_clean_extracted_text_handles_none_input(self):
        """clean_extracted_text should handle None input"""
        result = resume_parser.clean_extracted_text(None)
        assert result is None

    def test_clean_extracted_text_removes_multiple_spaces(self):
        """clean_extracted_text should replace multiple spaces with single space"""
        text = "Hello    world    test"
        result = resume_parser.clean_extracted_text(text)
        assert result == "Hello world test"

    def test_clean_extracted_text_removes_multiple_newlines(self):
        """clean_extracted_text should replace 3+ newlines with double newline"""
        text = "Paragraph 1\n\n\n\nParagraph 2"
        result = resume_parser.clean_extracted_text(text)
        assert result == "Paragraph 1\n\nParagraph 2"

    def test_clean_extracted_text_strips_line_whitespace(self):
        """clean_extracted_text should strip leading/trailing whitespace from lines"""
        text = "  Line 1  \n  Line 2  \n  Line 3  "
        result = resume_parser.clean_extracted_text(text)
        lines = result.split('\n')
        assert all(line == line.strip() for line in lines)

    def test_clean_extracted_text_strips_overall_whitespace(self):
        """clean_extracted_text should strip leading/trailing whitespace from text"""
        text = "\n\n  Text content  \n\n"
        result = resume_parser.clean_extracted_text(text)
        assert result == "Text content"

    def test_clean_extracted_text_preserves_double_newlines(self):
        """clean_extracted_text should preserve intentional paragraph breaks"""
        text = "Paragraph 1\n\nParagraph 2\n\nParagraph 3"
        result = resume_parser.clean_extracted_text(text)
        assert "\n\n" in result
        assert result.count("\n\n") == 2


class TestSupportedExtensions:
    """Test supported file extension functions"""

    def test_get_supported_extensions_always_includes_txt(self):
        """get_supported_extensions should always include .txt"""
        extensions = resume_parser.get_supported_extensions()
        assert ".txt" in extensions

    def test_get_supported_extensions_includes_pdf_when_available(self):
        """get_supported_extensions should include .pdf when pypdf available"""
        if resume_parser.PDF_AVAILABLE:
            extensions = resume_parser.get_supported_extensions()
            assert ".pdf" in extensions

    def test_get_supported_extensions_includes_docx_when_available(self):
        """get_supported_extensions should include .docx when python-docx available"""
        if resume_parser.DOCX_AVAILABLE:
            extensions = resume_parser.get_supported_extensions()
            assert ".docx" in extensions

    def test_get_supported_extensions_returns_list(self):
        """get_supported_extensions should return a list"""
        extensions = resume_parser.get_supported_extensions()
        assert isinstance(extensions, list)
        assert len(extensions) > 0


class TestParseResume:
    """Test main parse_resume function"""

    def test_parse_resume_with_empty_bytes(self):
        """parse_resume should handle empty file bytes"""
        text, warnings = resume_parser.parse_resume(b"", "test.txt")

        # Should return empty text or warning
        assert isinstance(text, str)
        assert isinstance(warnings, list)

    def test_parse_resume_with_no_filename(self):
        """parse_resume should handle missing filename"""
        text, warnings = resume_parser.parse_resume(b"test content", "")

        assert text == ""
        assert len(warnings) > 0
        assert any("filename" in w.lower() for w in warnings)

    def test_parse_resume_with_unsupported_extension(self):
        """parse_resume should reject unsupported file types"""
        text, warnings = resume_parser.parse_resume(b"test", "resume.xyz")

        assert text == ""
        assert len(warnings) > 0
        assert any("unsupported" in w.lower() for w in warnings)

    def test_parse_resume_txt_file(self):
        """parse_resume should parse .txt files"""
        content = "John Doe\nSoftware Engineer\nExperience with Python"
        text, warnings = resume_parser.parse_resume(content.encode('utf-8'), "resume.txt")

        assert "John Doe" in text
        assert "Software Engineer" in text
        assert "Python" in text

    def test_parse_resume_detects_extension_case_insensitive(self):
        """parse_resume should handle extensions case-insensitively"""
        content = "Test resume content"

        text1, _ = resume_parser.parse_resume(content.encode('utf-8'), "resume.TXT")
        text2, _ = resume_parser.parse_resume(content.encode('utf-8'), "resume.txt")

        # Both should parse successfully
        assert text1 == text2


class TestParseTxt:
    """Test text file parsing"""

    def test_parse_txt_with_utf8_encoding(self):
        """parse_txt should handle UTF-8 encoded text"""
        content = "Resume with UTF-8: résumé café"
        text, warnings = resume_parser.parse_txt(content.encode('utf-8'))

        assert "résumé" in text
        assert "café" in text
        assert len(warnings) == 0

    def test_parse_txt_with_ascii_encoding(self):
        """parse_txt should handle ASCII encoded text"""
        content = "Simple ASCII resume"
        text, warnings = resume_parser.parse_txt(content.encode('ascii'))

        assert "Simple ASCII resume" in text
        assert len(warnings) == 0

    def test_parse_txt_with_latin1_encoding(self):
        """parse_txt should handle Latin-1 encoded text"""
        content = "Resume with Latin-1 characters"
        text, warnings = resume_parser.parse_txt(content.encode('latin-1'))

        assert "Resume with Latin-1" in text


class TestFileSaveAndRetrieval:
    """Test file save and retrieval functions"""

    def test_save_resume_file_creates_file(self, temp_upload_dir):
        """save_resume_file should create file on disk"""
        file_bytes = b"Test resume content"
        filename = "resume.txt"
        candidate_id = 123

        path, error = resume_parser.save_resume_file(candidate_id, file_bytes, filename)

        assert error is None
        assert path is not None
        assert Path(path).exists()

    def test_save_resume_file_generates_unique_filename(self, temp_upload_dir):
        """save_resume_file should generate unique filename with timestamp"""
        import time
        file_bytes = b"Test content"
        candidate_id = 123

        path1, _ = resume_parser.save_resume_file(candidate_id, file_bytes, "resume.txt")
        time.sleep(1.1)  # Ensure different timestamp (timestamps are at second resolution)
        path2, _ = resume_parser.save_resume_file(candidate_id, file_bytes, "resume.txt")

        # Paths should be different due to timestamp
        assert path1 != path2

    def test_save_resume_file_sanitizes_filename(self, temp_upload_dir):
        """save_resume_file should sanitize malicious filenames"""
        file_bytes = b"Test content"
        candidate_id = 123
        malicious_filename = "../../../etc/passwd"

        path, error = resume_parser.save_resume_file(candidate_id, file_bytes, malicious_filename)

        # Should succeed but filename should be sanitized
        assert error is None
        assert "../" not in path
        assert "etc/passwd" not in path

    def test_save_resume_file_handles_no_file_data(self, temp_upload_dir):
        """save_resume_file should reject empty file bytes"""
        path, error = resume_parser.save_resume_file(123, b"", "resume.txt")

        assert path is None
        assert error is not None

    def test_save_resume_file_handles_no_filename(self, temp_upload_dir):
        """save_resume_file should reject missing filename"""
        path, error = resume_parser.save_resume_file(123, b"content", "")

        assert path is None
        assert error is not None

    def test_get_resume_file_retrieves_saved_file(self, temp_upload_dir):
        """get_resume_file should retrieve saved file"""
        original_bytes = b"Test resume content"
        path, _ = resume_parser.save_resume_file(123, original_bytes, "resume.txt")

        retrieved_bytes, error = resume_parser.get_resume_file(path)

        assert error is None
        assert retrieved_bytes == original_bytes

    def test_get_resume_file_handles_nonexistent_file(self, temp_upload_dir):
        """get_resume_file should handle non-existent file path"""
        fake_path = str(temp_upload_dir / "nonexistent.txt")

        file_bytes, error = resume_parser.get_resume_file(fake_path)

        assert file_bytes is None
        assert error is not None
        assert "not found" in error.lower()

    def test_delete_resume_file_removes_file(self, temp_upload_dir):
        """delete_resume_file should remove file from disk"""
        file_bytes = b"Test content"
        path, _ = resume_parser.save_resume_file(123, file_bytes, "resume.txt")

        assert Path(path).exists()

        error = resume_parser.delete_resume_file(path)

        assert error is None
        assert not Path(path).exists()

    def test_delete_resume_file_handles_nonexistent_file(self, temp_upload_dir):
        """delete_resume_file should handle non-existent file gracefully"""
        fake_path = str(temp_upload_dir / "nonexistent.txt")

        error = resume_parser.delete_resume_file(fake_path)

        # Should succeed (no-op) when file doesn't exist
        assert error is None


class TestGetParseStatus:
    """Test parse status reporting"""

    def test_get_parse_status_returns_dict(self):
        """get_parse_status should return dictionary with status"""
        status = resume_parser.get_parse_status()

        assert isinstance(status, dict)
        assert "pdf" in status
        assert "docx" in status
        assert "txt" in status
        assert "supported_extensions" in status

    def test_get_parse_status_txt_always_true(self):
        """get_parse_status should show txt as always supported"""
        status = resume_parser.get_parse_status()

        assert status["txt"] is True

    def test_get_parse_status_includes_extensions(self):
        """get_parse_status should include supported extensions list"""
        status = resume_parser.get_parse_status()
        extensions = status["supported_extensions"]

        assert isinstance(extensions, list)
        assert ".txt" in extensions
