"""
Unit tests for XSS prevention utilities.

Tests cover:
- HTML tag escaping (<script>, <img>, etc.)
- HTML attribute escaping (event handlers, quotes)
- Special character escaping (&, <, >, ", ')
- None handling
- Type handling (integers, floats)
- Normal text preservation
"""
import pytest
from views.utils import safe


class TestSafeHTMLEscaping:
    """Test the safe() function for HTML escaping."""

    def test_safe_escapes_script_tags(self):
        """Test that safe() escapes script tags."""
        input_text = "<script>alert('xss')</script>"
        expected = "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert safe(input_text) == expected

    def test_safe_escapes_script_tag_with_src(self):
        """Test that safe() escapes script tags with src attribute."""
        input_text = '<script src="evil.js"></script>'
        expected = '&lt;script src=&quot;evil.js&quot;&gt;&lt;/script&gt;'
        assert safe(input_text) == expected

    def test_safe_escapes_img_tag_with_onerror(self):
        """Test that safe() escapes img tag with onerror event."""
        input_text = '<img src=x onerror="alert(1)">'
        expected = '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'
        assert safe(input_text) == expected

    def test_safe_escapes_iframe_tag(self):
        """Test that safe() escapes iframe tags."""
        input_text = '<iframe src="javascript:alert(1)"></iframe>'
        expected = '&lt;iframe src=&quot;javascript:alert(1)&quot;&gt;&lt;/iframe&gt;'
        assert safe(input_text) == expected

    def test_safe_escapes_anchor_with_javascript(self):
        """Test that safe() escapes anchor tags with javascript: protocol."""
        input_text = '<a href="javascript:void(0)">Click</a>'
        expected = '&lt;a href=&quot;javascript:void(0)&quot;&gt;Click&lt;/a&gt;'
        assert safe(input_text) == expected

    def test_safe_escapes_div_with_onclick(self):
        """Test that safe() escapes div with onclick event."""
        input_text = '<div onclick="alert(1)">Click me</div>'
        expected = '&lt;div onclick=&quot;alert(1)&quot;&gt;Click me&lt;/div&gt;'
        assert safe(input_text) == expected


class TestSafeAttributeEscaping:
    """Test attribute escaping for XSS prevention."""

    def test_safe_escapes_double_quote_onmouseover(self):
        """Test that safe() escapes double quote with onmouseover."""
        input_text = '" onmouseover="alert(1)'
        expected = '&quot; onmouseover=&quot;alert(1)'
        assert safe(input_text) == expected

    def test_safe_escapes_single_quote_injection(self):
        """Test that safe() escapes single quote injection."""
        input_text = "' onload='alert(1)"
        expected = "&#x27; onload=&#x27;alert(1)"
        assert safe(input_text) == expected

    def test_safe_escapes_mixed_quotes(self):
        """Test that safe() escapes mixed quotes."""
        input_text = '''Test "double" and 'single' quotes'''
        expected = '''Test &quot;double&quot; and &#x27;single&#x27; quotes'''
        assert safe(input_text) == expected

    def test_safe_escapes_style_attribute_injection(self):
        """Test that safe() escapes style attribute with expression."""
        input_text = 'x" style="background:url(javascript:alert(1))'
        expected = 'x&quot; style=&quot;background:url(javascript:alert(1))'
        assert safe(input_text) == expected


class TestSafeSpecialCharacters:
    """Test escaping of special HTML characters."""

    def test_safe_escapes_ampersand(self):
        """Test that safe() escapes ampersand."""
        input_text = "Tom & Jerry"
        expected = "Tom &amp; Jerry"
        assert safe(input_text) == expected

    def test_safe_escapes_less_than(self):
        """Test that safe() escapes less than symbol."""
        input_text = "5 < 10"
        expected = "5 &lt; 10"
        assert safe(input_text) == expected

    def test_safe_escapes_greater_than(self):
        """Test that safe() escapes greater than symbol."""
        input_text = "10 > 5"
        expected = "10 &gt; 5"
        assert safe(input_text) == expected

    def test_safe_escapes_double_quotes(self):
        """Test that safe() escapes double quotes."""
        input_text = 'He said "Hello"'
        expected = 'He said &quot;Hello&quot;'
        assert safe(input_text) == expected

    def test_safe_escapes_single_quotes(self):
        """Test that safe() escapes single quotes (apostrophes)."""
        input_text = "It's a test"
        expected = "It&#x27;s a test"
        assert safe(input_text) == expected

    def test_safe_escapes_multiple_ampersands(self):
        """Test that safe() correctly escapes multiple ampersands."""
        input_text = "A&B&C&D"
        expected = "A&amp;B&amp;C&amp;D"
        assert safe(input_text) == expected


class TestSafeNoneHandling:
    """Test safe() handling of None values."""

    def test_safe_handles_none_gracefully(self):
        """Test that safe() handles None and returns empty string."""
        assert safe(None) == ''

    def test_safe_with_none_in_template_context(self):
        """Test that safe() can be used safely with None in templates."""
        # This simulates using safe() on an optional field that might be None
        user_bio = None
        result = f"Bio: {safe(user_bio)}"
        assert result == "Bio: "


class TestSafeTypeHandling:
    """Test safe() handling of different data types."""

    def test_safe_handles_integers(self):
        """Test that safe() handles integers."""
        assert safe(42) == '42'
        assert safe(0) == '0'
        assert safe(-100) == '-100'

    def test_safe_handles_floats(self):
        """Test that safe() handles floats."""
        assert safe(3.14) == '3.14'
        assert safe(0.0) == '0.0'
        assert safe(-2.5) == '-2.5'

    def test_safe_handles_boolean(self):
        """Test that safe() handles booleans."""
        assert safe(True) == 'True'
        assert safe(False) == 'False'

    def test_safe_handles_empty_string(self):
        """Test that safe() handles empty string."""
        assert safe('') == ''


class TestSafeNormalText:
    """Test that safe() preserves normal text."""

    def test_safe_preserves_normal_text(self):
        """Test that safe() preserves normal text without special characters."""
        input_text = "Hello World"
        assert safe(input_text) == "Hello World"

    def test_safe_preserves_alphanumeric(self):
        """Test that safe() preserves alphanumeric text."""
        input_text = "User123 has logged in"
        assert safe(input_text) == "User123 has logged in"

    def test_safe_preserves_whitespace(self):
        """Test that safe() preserves whitespace."""
        input_text = "Line 1\nLine 2\tTabbed"
        assert safe(input_text) == "Line 1\nLine 2\tTabbed"

    def test_safe_preserves_unicode(self):
        """Test that safe() preserves Unicode characters."""
        input_text = "Hello 世界 🌍"
        assert safe(input_text) == "Hello 世界 🌍"

    def test_safe_preserves_punctuation(self):
        """Test that safe() preserves safe punctuation."""
        input_text = "Hello, world! How are you?"
        assert safe(input_text) == "Hello, world! How are you?"


class TestSafeComplexXSSAttempts:
    """Test safe() against complex XSS attack vectors."""

    def test_safe_blocks_svg_xss(self):
        """Test that safe() blocks SVG-based XSS."""
        input_text = '<svg onload="alert(1)">'
        expected = '&lt;svg onload=&quot;alert(1)&quot;&gt;'
        assert safe(input_text) == expected

    def test_safe_blocks_base64_encoded_script(self):
        """Test that safe() escapes base64 encoded script attempts."""
        input_text = '<img src="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">'
        expected = '&lt;img src=&quot;data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==&quot;&gt;'
        assert safe(input_text) == expected

    def test_safe_blocks_event_handler_without_quotes(self):
        """Test that safe() blocks event handlers without quotes."""
        input_text = "<body onload=alert(1)>"
        expected = "&lt;body onload=alert(1)&gt;"
        assert safe(input_text) == expected

    def test_safe_blocks_nested_tags(self):
        """Test that safe() blocks nested malicious tags."""
        input_text = "<div><script>alert('nested')</script></div>"
        expected = "&lt;div&gt;&lt;script&gt;alert(&#x27;nested&#x27;)&lt;/script&gt;&lt;/div&gt;"
        assert safe(input_text) == expected

    def test_safe_blocks_html_entity_bypass_attempt(self):
        """Test that safe() blocks attempts to bypass using HTML entities."""
        input_text = "&lt;script&gt;alert(1)&lt;/script&gt;"
        expected = "&amp;lt;script&amp;gt;alert(1)&amp;lt;/script&amp;gt;"
        assert safe(input_text) == expected

    def test_safe_blocks_comment_injection(self):
        """Test that safe() escapes HTML comment injection."""
        input_text = "<!--<script>alert(1)</script>-->"
        expected = "&lt;!--&lt;script&gt;alert(1)&lt;/script&gt;--&gt;"
        assert safe(input_text) == expected

    def test_safe_blocks_object_tag(self):
        """Test that safe() escapes object tags."""
        input_text = '<object data="javascript:alert(1)"></object>'
        expected = '&lt;object data=&quot;javascript:alert(1)&quot;&gt;&lt;/object&gt;'
        assert safe(input_text) == expected

    def test_safe_blocks_embed_tag(self):
        """Test that safe() escapes embed tags."""
        input_text = '<embed src="javascript:alert(1)">'
        expected = '&lt;embed src=&quot;javascript:alert(1)&quot;&gt;'
        assert safe(input_text) == expected


class TestSafeRealWorldScenarios:
    """Test safe() with real-world scenarios."""

    def test_safe_with_user_name_xss_attempt(self):
        """Test safe() with malicious username."""
        username = "<script>alert('XSS')</script>Admin"
        escaped = safe(username)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_safe_with_email_xss_attempt(self):
        """Test safe() with malicious email."""
        email = 'user@example.com"><script>alert(1)</script>'
        escaped = safe(email)
        assert "<script>" not in escaped
        assert "&quot;&gt;&lt;script&gt;" in escaped

    def test_safe_with_comment_xss_attempt(self):
        """Test safe() with malicious comment."""
        comment = "Great job! <img src=x onerror=alert(1)>"
        escaped = safe(comment)
        # The key XSS elements should be escaped
        assert "<img" not in escaped  # Tag is escaped
        assert "&lt;img" in escaped  # Should be escaped form
        assert "alert(1)" in escaped  # Content is preserved but safe

    def test_safe_with_url_parameter(self):
        """Test safe() with URL containing XSS attempt."""
        url = 'https://example.com?redirect="><script>alert(1)</script>'
        escaped = safe(url)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_safe_with_json_payload(self):
        """Test safe() with JSON containing XSS."""
        json_str = '{"name": "<script>alert(1)</script>"}'
        escaped = safe(json_str)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_safe_with_multiline_xss(self):
        """Test safe() with multiline XSS attempt."""
        multiline = """<script>
        alert('XSS');
        document.cookie;
        </script>"""
        escaped = safe(multiline)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped
        assert "&lt;/script&gt;" in escaped


class TestSafeEdgeCases:
    """Test edge cases for safe() function."""

    def test_safe_with_very_long_string(self):
        """Test safe() with very long string."""
        long_string = "A" * 10000 + "<script>alert(1)</script>"
        escaped = safe(long_string)
        assert "<script>" not in escaped
        assert len(escaped) > 10000

    def test_safe_with_repeated_escaping(self):
        """Test that safe() can be called multiple times (idempotent for already escaped)."""
        input_text = "Tom & Jerry"
        once = safe(input_text)
        twice = safe(once)

        # First: Tom & Jerry -> Tom &amp; Jerry
        # Second: Tom &amp; Jerry -> Tom &amp;amp; Jerry (double escaping)
        # Note: safe() is NOT idempotent - it will double-escape
        assert once == "Tom &amp; Jerry"
        assert twice == "Tom &amp;amp; Jerry"

    def test_safe_with_only_special_characters(self):
        """Test safe() with string containing only special characters."""
        input_text = "<>&\"'"
        escaped = safe(input_text)
        assert escaped == "&lt;&gt;&amp;&quot;&#x27;"

    def test_safe_with_mixed_content(self):
        """Test safe() with mixed safe and unsafe content."""
        input_text = "Hello <script>alert(1)</script> World & Universe"
        escaped = safe(input_text)
        assert "Hello" in escaped
        assert "World" in escaped
        assert "Universe" in escaped
        assert "<script>" not in escaped
        assert "&amp;" in escaped


class TestSafeDocumentation:
    """Test that safe() behavior matches documentation expectations."""

    def test_safe_is_suitable_for_html_content(self):
        """Test that safe() output can be safely inserted into HTML content."""
        user_input = '<img src=x onerror="alert(1)">'
        escaped = safe(user_input)

        # Simulate inserting into HTML
        html = f"<div>{escaped}</div>"

        # Verify no unescaped tags remain
        assert '<img' not in html or '&lt;img' in html
        assert 'onerror="' not in html or 'onerror=&quot;' in html

    def test_safe_is_suitable_for_html_attributes(self):
        """Test that safe() output can be safely inserted into HTML attributes."""
        user_input = '" onmouseover="alert(1)'
        escaped = safe(user_input)

        # Simulate inserting into attribute
        html = f'<div title="{escaped}">Content</div>'

        # Verify quotes are escaped
        assert '&quot;' in escaped
        # The attack vector should be neutralized
        assert 'onmouseover="alert' not in html or '&quot; onmouseover=&quot;' in html
