"""
Unit tests for file upload security features in resume_parser.py.

Tests cover:
- File magic byte validation (PDF, DOCX, TXT)
- Fake file extension detection (EXE disguised as TXT, etc.)
- Null byte injection prevention in filenames
- Path traversal prevention (../../etc/passwd)
- Filename length limits
- File containment within UPLOAD_DIR
- Suspicious content detection in extracted text
- File size validation
- PDF page limit enforcement
- ZIP bomb prevention (for DOCX files)
"""
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from resume_parser import (
    validate_file_magic,
    save_resume_file,
    scan_file_content,
    validate_file_size,
    parse_pdf,
    check_zip_bomb,
    UPLOAD_DIR,
)


class TestValidateFileMagic:
    """Test file magic byte validation."""

    def test_validate_file_magic_accepts_valid_pdf(self):
        """Test that validate_file_magic accepts valid PDF (starts with %PDF)."""
        pdf_bytes = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\nSome PDF content'
        is_valid, error = validate_file_magic(pdf_bytes, '.pdf')

        assert is_valid is True
        assert error is None

    def test_validate_file_magic_rejects_fake_pdf(self):
        """Test that validate_file_magic rejects fake PDF (wrong magic bytes)."""
        fake_pdf = b'This is not a PDF file'
        is_valid, error = validate_file_magic(fake_pdf, '.pdf')

        assert is_valid is False
        assert error is not None
        assert "PDF" in error or "magic" in error.lower()

    def test_validate_file_magic_accepts_valid_docx(self):
        """Test that validate_file_magic accepts valid DOCX (starts with PK)."""
        docx_bytes = b'PK\x03\x04\x14\x00\x00\x00'  # ZIP header
        is_valid, error = validate_file_magic(docx_bytes, '.docx')

        assert is_valid is True
        assert error is None

    def test_validate_file_magic_rejects_fake_docx(self):
        """Test that validate_file_magic rejects fake DOCX."""
        fake_docx = b'This is not a DOCX file'
        is_valid, error = validate_file_magic(fake_docx, '.docx')

        assert is_valid is False
        assert error is not None
        assert "DOCX" in error or "magic" in error.lower()

    def test_validate_file_magic_rejects_exe_as_txt(self):
        """Test that validate_file_magic rejects EXE disguised as TXT."""
        # Windows EXE starts with MZ
        exe_bytes = b'MZ\x90\x00\x03\x00\x00\x00'
        is_valid, error = validate_file_magic(exe_bytes, '.txt')

        assert is_valid is False
        assert error is not None
        assert "executable" in error.lower() or "EXE" in error or "not a text" in error

    def test_validate_file_magic_rejects_pdf_as_txt(self):
        """Test that validate_file_magic rejects PDF disguised as TXT."""
        pdf_bytes = b'%PDF-1.4\nContent'
        is_valid, error = validate_file_magic(pdf_bytes, '.txt')

        assert is_valid is False
        assert error is not None
        assert "PDF" in error

    def test_validate_file_magic_rejects_docx_as_txt(self):
        """Test that validate_file_magic rejects DOCX disguised as TXT."""
        docx_bytes = b'PK\x03\x04\x14\x00\x00\x00'
        is_valid, error = validate_file_magic(docx_bytes, '.txt')

        assert is_valid is False
        assert error is not None
        assert "ZIP" in error or "DOCX" in error

    def test_validate_file_magic_accepts_valid_txt(self):
        """Test that validate_file_magic accepts valid text file."""
        txt_bytes = b'This is a plain text resume file.\nName: John Doe'
        is_valid, error = validate_file_magic(txt_bytes, '.txt')

        assert is_valid is True
        assert error is None

    def test_validate_file_magic_rejects_jpeg_as_txt(self):
        """Test that validate_file_magic rejects JPEG disguised as TXT."""
        jpeg_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        is_valid, error = validate_file_magic(jpeg_bytes, '.txt')

        assert is_valid is False
        assert error is not None
        assert "JPEG" in error or "image" in error.lower()

    def test_validate_file_magic_rejects_png_as_txt(self):
        """Test that validate_file_magic rejects PNG disguised as TXT."""
        png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        is_valid, error = validate_file_magic(png_bytes, '.txt')

        assert is_valid is False
        assert error is not None
        assert "PNG" in error or "image" in error.lower()

    def test_validate_file_magic_rejects_elf_binary_as_txt(self):
        """Test that validate_file_magic rejects ELF binary disguised as TXT."""
        elf_bytes = b'\x7fELF\x01\x01\x01\x00'
        is_valid, error = validate_file_magic(elf_bytes, '.txt')

        assert is_valid is False
        assert error is not None
        assert "ELF" in error or "binary" in error.lower()

    def test_validate_file_magic_rejects_empty_file(self):
        """Test that validate_file_magic rejects empty file."""
        is_valid, error = validate_file_magic(b'', '.pdf')

        assert is_valid is False
        assert error is not None

    def test_validate_file_magic_rejects_too_small_file(self):
        """Test that validate_file_magic rejects file too small to validate."""
        is_valid, error = validate_file_magic(b'AB', '.pdf')

        assert is_valid is False
        assert error is not None
        assert "small" in error.lower()

    def test_validate_file_magic_rejects_unsupported_extension(self):
        """Test that validate_file_magic rejects unsupported extension."""
        is_valid, error = validate_file_magic(b'Some content', '.exe')

        assert is_valid is False
        assert error is not None
        assert "unsupported" in error.lower() or "extension" in error.lower()


class TestSaveResumeFile:
    """Test save_resume_file security features."""

    def test_save_resume_file_rejects_null_bytes_in_filename(self, temp_upload_dir):
        """Test that save_resume_file rejects null bytes in filename."""
        file_bytes = b'Resume content'
        filename = 'resume\x00.pdf'  # Null byte injection attempt

        file_path, error = save_resume_file(1, file_bytes, filename)

        assert file_path is None
        assert error is not None
        assert "null" in error.lower()

    def test_save_resume_file_rejects_path_traversal_simple(self, temp_upload_dir):
        """Test that save_resume_file rejects simple path traversal."""
        file_bytes = b'Resume content'
        filename = '../../etc/passwd'

        file_path, error = save_resume_file(1, file_bytes, filename)

        # Path traversal should be sanitized - the dangerous parts removed
        # The file should be saved with a safe name (just 'passwd')
        if file_path:
            # Verify it's within the temp_upload_dir
            saved_path = Path(file_path).resolve()
            upload_dir_resolved = temp_upload_dir.resolve()
            assert str(saved_path).startswith(str(upload_dir_resolved)), \
                f"File saved outside upload dir: {saved_path}"
            # Should not contain 'etc' in the path
            assert 'etc' not in str(saved_path).lower()
        else:
            # Or it should be rejected
            assert error is not None

    def test_save_resume_file_rejects_path_traversal_complex(self, temp_upload_dir):
        """Test that save_resume_file rejects complex path traversal."""
        file_bytes = b'Resume content'
        filename = '..\\..\\..\\windows\\system32\\evil.exe'

        file_path, error = save_resume_file(1, file_bytes, filename)

        # Should sanitize the path
        if file_path:
            saved_path = Path(file_path).resolve()
            upload_dir_resolved = temp_upload_dir.resolve()
            assert str(saved_path).startswith(str(upload_dir_resolved)), \
                f"File saved outside upload dir: {saved_path}"
            # Dangerous path components should be removed
            assert 'windows' not in str(saved_path).lower()
            assert 'system32' not in str(saved_path).lower()
        else:
            assert error is not None

    def test_save_resume_file_rejects_absolute_path(self, temp_upload_dir):
        """Test that save_resume_file rejects absolute path."""
        file_bytes = b'Resume content'
        filename = '/etc/passwd'

        file_path, error = save_resume_file(1, file_bytes, filename)

        # Should sanitize to just 'passwd' or similar
        if file_path:
            saved_path = Path(file_path).resolve()
            upload_dir_resolved = temp_upload_dir.resolve()
            assert str(saved_path).startswith(str(upload_dir_resolved)), \
                f"File saved outside upload dir: {saved_path}"
            # Path should not contain 'etc'
            assert 'etc' not in str(saved_path).lower()

    def test_save_resume_file_rejects_filename_too_long(self, temp_upload_dir, monkeypatch):
        """Test that save_resume_file rejects filenames over MAX_FILENAME_LENGTH."""
        from config import settings
        monkeypatch.setattr(settings, 'MAX_FILENAME_LENGTH', 50)

        file_bytes = b'Resume content'
        # Create a filename longer than 50 characters
        filename = 'a' * 60 + '.pdf'

        file_path, error = save_resume_file(1, file_bytes, filename)

        assert file_path is None
        assert error is not None
        assert "too long" in error.lower() or "max" in error.lower()

    def test_save_resume_file_keeps_file_within_upload_dir(self, temp_upload_dir):
        """Test that save_resume_file keeps file within UPLOAD_DIR (temp_upload_dir in tests)."""
        file_bytes = b'Resume content'
        filename = 'legitimate_resume.pdf'

        file_path, error = save_resume_file(1, file_bytes, filename)

        assert error is None
        assert file_path is not None

        # Verify file is within temp_upload_dir (which is patched as UPLOAD_DIR)
        saved_path = Path(file_path).resolve()
        upload_dir_resolved = temp_upload_dir.resolve()

        assert str(saved_path).startswith(str(upload_dir_resolved)), \
            f"File not in upload dir: {saved_path} not in {upload_dir_resolved}"

    def test_save_resume_file_sanitizes_special_characters(self, temp_upload_dir):
        """Test that save_resume_file sanitizes special characters in filename."""
        file_bytes = b'Resume content'
        filename = 'resume<>:|?*.pdf'

        file_path, error = save_resume_file(1, file_bytes, filename)

        # Should sanitize or reject
        if file_path:
            path_obj = Path(file_path)
            filename_part = path_obj.name
            # Special characters should be removed
            assert '<' not in filename_part
            assert '>' not in filename_part
            assert '|' not in filename_part
            assert '?' not in filename_part
            assert '*' not in filename_part

    def test_save_resume_file_creates_unique_filename(self, temp_upload_dir):
        """Test that save_resume_file creates unique filename with timestamp."""
        file_bytes = b'Resume content'
        filename = 'resume.pdf'

        file_path1, error1 = save_resume_file(1, file_bytes, filename)

        # Sleep 1+ second to ensure different timestamp (format is %Y%m%d_%H%M%S)
        import time
        time.sleep(1.1)

        file_path2, error2 = save_resume_file(1, file_bytes, filename)

        assert error1 is None and error2 is None
        # Filenames should be different due to timestamp
        assert file_path1 != file_path2, \
            f"Filenames should be unique: {file_path1} == {file_path2}"

    def test_save_resume_file_preserves_extension(self, temp_upload_dir):
        """Test that save_resume_file preserves file extension."""
        file_bytes = b'Resume content'
        filename = 'resume.pdf'

        file_path, error = save_resume_file(1, file_bytes, filename)

        assert error is None
        assert file_path.endswith('.pdf')

    def test_save_resume_file_rejects_empty_bytes(self, temp_upload_dir):
        """Test that save_resume_file rejects empty file bytes."""
        file_bytes = b''
        filename = 'resume.pdf'

        file_path, error = save_resume_file(1, file_bytes, filename)

        assert file_path is None
        assert error is not None

    def test_save_resume_file_rejects_empty_filename(self, temp_upload_dir):
        """Test that save_resume_file rejects empty filename."""
        file_bytes = b'Resume content'
        filename = ''

        file_path, error = save_resume_file(1, file_bytes, filename)

        assert file_path is None
        assert error is not None


class TestScanFileContent:
    """Test scan_file_content for suspicious patterns."""

    def test_scan_file_content_detects_binary_long_lines(self):
        """Test that scan_file_content detects extremely long lines (binary data)."""
        # Create text with a very long line (>10000 chars)
        long_line = 'A' * 15000
        text = f"Normal line\n{long_line}\nAnother line"

        is_clean, warnings = scan_file_content(text)

        assert is_clean is False
        assert len(warnings) > 0
        assert any("long line" in w.lower() for w in warnings)

    def test_scan_file_content_detects_non_printable_characters(self):
        """Test that scan_file_content detects high ratio of non-printable characters."""
        # Create text with many non-printable characters
        text = "Normal text " + '\x01' * 100 + '\x02' * 100 + '\x03' * 100

        is_clean, warnings = scan_file_content(text)

        # Should flag high ratio of non-printable characters
        assert is_clean is False
        assert len(warnings) > 0
        assert any("printable" in w.lower() for w in warnings)

    def test_scan_file_content_detects_null_bytes(self):
        """Test that scan_file_content detects null bytes in text."""
        text = "Normal text\x00with null\x00bytes"

        is_clean, warnings = scan_file_content(text)

        assert is_clean is False
        assert len(warnings) > 0
        assert any("null" in w.lower() for w in warnings)

    def test_scan_file_content_accepts_clean_text(self):
        """Test that scan_file_content accepts clean text."""
        text = """
        John Doe
        Senior Software Engineer
        Email: john@example.com

        EXPERIENCE
        - Developed Python applications
        - Worked with AWS and Docker

        EDUCATION
        BS Computer Science
        """

        is_clean, warnings = scan_file_content(text)

        assert is_clean is True
        assert len(warnings) == 0

    def test_scan_file_content_handles_empty_text(self):
        """Test that scan_file_content handles empty text."""
        is_clean, warnings = scan_file_content("")

        assert is_clean is True
        assert len(warnings) == 0

    def test_scan_file_content_allows_normal_unicode(self):
        """Test that scan_file_content allows normal Unicode characters."""
        text = "Resume with Unicode: José García, 日本語, emoji 🎉"

        is_clean, warnings = scan_file_content(text)

        assert is_clean is True
        assert len(warnings) == 0


class TestValidateFileSize:
    """Test validate_file_size enforcement."""

    def test_validate_file_size_accepts_within_limit(self, monkeypatch):
        """Test that validate_file_size accepts files within limit."""
        from config import settings
        monkeypatch.setattr(settings, 'MAX_RESUME_SIZE_MB', 10.0)

        # Create 5 MB file
        file_bytes = b'A' * (5 * 1024 * 1024)

        error = validate_file_size(file_bytes, max_size_mb=10.0)

        assert error is None

    def test_validate_file_size_rejects_over_limit(self, monkeypatch):
        """Test that validate_file_size rejects files over limit."""
        from config import settings
        monkeypatch.setattr(settings, 'MAX_RESUME_SIZE_MB', 10.0)

        # Create 15 MB file
        file_bytes = b'A' * (15 * 1024 * 1024)

        error = validate_file_size(file_bytes, max_size_mb=10.0)

        assert error is not None
        assert "too large" in error.lower() or "exceeds" in error.lower()

    def test_validate_file_size_uses_default_from_settings(self, monkeypatch):
        """Test that validate_file_size uses default from settings."""
        from config import settings
        monkeypatch.setattr(settings, 'MAX_RESUME_SIZE_MB', 5.0)

        # Create 6 MB file
        file_bytes = b'A' * (6 * 1024 * 1024)

        error = validate_file_size(file_bytes)  # No max_size_mb parameter

        assert error is not None

    def test_validate_file_size_handles_empty_file(self):
        """Test that validate_file_size handles empty file."""
        error = validate_file_size(b'')

        assert error is not None
        assert "no file" in error.lower()

    def test_validate_file_size_boundary_condition(self):
        """Test validate_file_size at exact boundary."""
        # Create file at exactly 10 MB
        file_bytes = b'A' * (10 * 1024 * 1024)

        error = validate_file_size(file_bytes, max_size_mb=10.0)

        # At exact limit should be accepted
        assert error is None


class TestPDFPageLimit:
    """Test PDF page limit enforcement."""

    @pytest.mark.skipif(not pytest.importorskip("pypdf", minversion=None), reason="pypdf not available")
    def test_parse_pdf_enforces_max_pages(self, monkeypatch):
        """Test that parse_pdf enforces MAX_PDF_PAGES limit."""
        from config import settings
        monkeypatch.setattr(settings, 'MAX_PDF_PAGES', 5)

        # Mock PdfReader to simulate a PDF with many pages
        with patch('resume_parser.PdfReader') as mock_reader_class:
            mock_reader = Mock()
            # Simulate 10 pages (over the limit of 5)
            mock_reader.pages = [Mock() for _ in range(10)]
            mock_reader_class.return_value = mock_reader

            pdf_bytes = b'%PDF-1.4\nMock PDF content'
            text, warnings = parse_pdf(pdf_bytes)

            # Should reject with warning about page limit
            assert text == ""
            assert len(warnings) > 0
            assert any("page limit" in w.lower() or "exceeds" in w.lower() for w in warnings)

    @pytest.mark.skipif(not pytest.importorskip("pypdf", minversion=None), reason="pypdf not available")
    def test_parse_pdf_accepts_within_page_limit(self, monkeypatch):
        """Test that parse_pdf accepts PDF within page limit."""
        from config import settings
        monkeypatch.setattr(settings, 'MAX_PDF_PAGES', 10)

        # Mock PdfReader to simulate a PDF with few pages
        with patch('resume_parser.PdfReader') as mock_reader_class:
            mock_reader = Mock()
            # Simulate 5 pages (within limit of 10)
            mock_page = Mock()
            mock_page.extract_text.return_value = "Sample resume text"
            mock_reader.pages = [mock_page for _ in range(5)]
            mock_reader_class.return_value = mock_reader

            pdf_bytes = b'%PDF-1.4\nMock PDF content'
            text, warnings = parse_pdf(pdf_bytes)

            # Should succeed
            assert text != ""
            # No warnings about page limit
            page_limit_warnings = [w for w in warnings if "page limit" in w.lower() or "exceeds" in w.lower()]
            assert len(page_limit_warnings) == 0


class TestZipBombPrevention:
    """Test ZIP bomb prevention for DOCX files."""

    def test_check_zip_bomb_accepts_normal_docx(self, monkeypatch):
        """Test that check_zip_bomb accepts normal DOCX file."""
        from config import settings
        monkeypatch.setattr(settings, 'MAX_DECOMPRESSED_SIZE_MB', 50.0)

        # Create a mock ZIP file with reasonable decompressed size
        import zipfile
        import io

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add small files (total 1 MB decompressed)
            zf.writestr('document.xml', 'A' * (1024 * 1024))

        zip_bytes = zip_buffer.getvalue()

        is_safe, error = check_zip_bomb(zip_bytes)

        assert is_safe is True
        assert error is None

    def test_check_zip_bomb_detects_oversized_decompression(self, monkeypatch):
        """Test that check_zip_bomb detects oversized decompression."""
        from config import settings
        monkeypatch.setattr(settings, 'MAX_DECOMPRESSED_SIZE_MB', 50.0)

        # Mock a ZIP file with huge decompressed size
        import zipfile
        import io

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add file that would decompress to 100 MB (over 50 MB limit)
            # Use low compression to simulate zip bomb
            zf.writestr('huge_file.txt', 'A' * (100 * 1024 * 1024))

        zip_bytes = zip_buffer.getvalue()

        is_safe, error = check_zip_bomb(zip_bytes)

        assert is_safe is False
        assert error is not None
        assert "exceeds limit" in error.lower() or "zip bomb" in error.lower()

    def test_check_zip_bomb_handles_invalid_zip(self):
        """Test that check_zip_bomb handles invalid ZIP file."""
        invalid_zip = b'This is not a ZIP file'

        is_safe, error = check_zip_bomb(invalid_zip)

        assert is_safe is False
        assert error is not None
        assert "zip" in error.lower() or "invalid" in error.lower()


class TestIntegrationPathTraversal:
    """Integration tests for path traversal prevention."""

    def test_path_traversal_blocked_by_path_resolve(self, temp_upload_dir):
        """Test that path traversal is blocked by path resolution check."""
        file_bytes = b'Malicious content'
        # Various path traversal attempts
        attack_filenames = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\evil.exe',
            './../../secret.txt',
            'subdir/../../escape.txt',
        ]

        for filename in attack_filenames:
            file_path, error = save_resume_file(999, file_bytes, filename)

            # File should either be rejected or contained within temp_upload_dir
            if file_path:
                saved_path = Path(file_path).resolve()
                upload_dir_resolved = temp_upload_dir.resolve()
                assert str(saved_path).startswith(str(upload_dir_resolved)), \
                    f"Path traversal not blocked for: {filename}. Saved to {saved_path}, expected in {upload_dir_resolved}"


class TestFilenameEdgeCases:
    """Test edge cases in filename handling."""

    def test_filename_with_unicode(self, temp_upload_dir):
        """Test that filenames with Unicode are handled."""
        file_bytes = b'Resume content'
        filename = 'résumé_日本語.pdf'

        file_path, error = save_resume_file(1, file_bytes, filename)

        # Should either accept or sanitize
        if file_path:
            assert Path(file_path).exists()

    def test_filename_with_spaces(self, temp_upload_dir):
        """Test that filenames with spaces are handled."""
        file_bytes = b'Resume content'
        filename = 'my resume file.pdf'

        file_path, error = save_resume_file(1, file_bytes, filename)

        # Should be handled (spaces might be kept or replaced)
        if file_path:
            assert Path(file_path).exists()

    def test_filename_all_special_chars_removed(self, temp_upload_dir):
        """Test filename with all special characters removed."""
        file_bytes = b'Resume content'
        filename = '<>:|?*.pdf'  # All special chars

        file_path, error = save_resume_file(1, file_bytes, filename)

        # Should handle gracefully (use default name or reject)
        # If saved, should have a valid filename
        if file_path:
            path_obj = Path(file_path)
            assert path_obj.name != ''
            assert path_obj.suffix == '.pdf'
