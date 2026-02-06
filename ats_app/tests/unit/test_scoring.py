"""
Unit tests for AI scoring module (genai.py)

Tests AI resume scoring, interview question generation, and note summarization.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ats_app'))

import genai


class TestAnthropicClientAccess:
    """Test Anthropic client initialization"""

    def test_get_anthropic_client_returns_none_when_unavailable(self):
        """get_anthropic_client should return None when anthropic not installed"""
        with patch.object(genai, 'ANTHROPIC_AVAILABLE', False):
            client = genai.get_anthropic_client()
            assert client is None

    def test_get_anthropic_client_returns_none_without_api_key(self):
        """get_anthropic_client should return None without API key"""
        with patch.object(genai, 'ANTHROPIC_AVAILABLE', True):
            with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}, clear=True):
                client = genai.get_anthropic_client()
                assert client is None


class TestResumeScoring:
    """Test resume scoring functions"""

    def test_smart_score_resume_returns_score_and_analysis(self, mock_anthropic_client):
        """smart_score_resume should return score and analysis"""
        resume_text = "Experienced Python developer with AWS and ML expertise"
        job_description = "Looking for Python developer with cloud experience"

        score, analysis = genai.smart_score_resume(resume_text, job_description)

        assert isinstance(score, (int, float))
        assert 0 <= score <= 100
        assert isinstance(analysis, str)
        assert len(analysis) > 0

    def test_smart_score_resume_handles_missing_resume(self):
        """smart_score_resume should handle missing resume text"""
        score, analysis = genai.smart_score_resume("", "Job description")

        assert score == 0.0
        assert "missing" in analysis.lower() or "unavailable" in analysis.lower()

    def test_smart_score_resume_handles_missing_job_description(self):
        """smart_score_resume should handle missing job description"""
        score, analysis = genai.smart_score_resume("Resume text", "")

        assert score == 0.0
        assert "missing" in analysis.lower() or "unavailable" in analysis.lower()

    def test_score_resume_against_jd_parses_json_response(self, mock_anthropic_client):
        """score_resume_against_jd should parse JSON response from AI"""
        mock_response = Mock()
        mock_response.content = [Mock(
            text='{"score": 85, "analysis": "Strong match", "strengths": ["Python"], "gaps": []}'
        )]
        mock_anthropic_client.messages.create.return_value = mock_response

        with patch('genai.get_anthropic_client', return_value=mock_anthropic_client):
            score, analysis = genai.score_resume_against_jd(
                "Resume text",
                "Job description"
            )

            assert score == 85.0
            assert "Strong match" in analysis
            assert "Python" in analysis

    def test_score_resume_against_jd_handles_api_failure(self):
        """score_resume_against_jd should handle API failure gracefully"""
        with patch('genai.invoke_claude', return_value=None):
            score, analysis = genai.score_resume_against_jd(
                "Resume text",
                "Job description"
            )

            assert score == 0.0
            assert "unavailable" in analysis.lower() or "manual review" in analysis.lower()

    def test_score_resume_against_jd_handles_malformed_json(self):
        """score_resume_against_jd should handle malformed JSON response"""
        with patch('genai.invoke_claude', return_value="This is not JSON at all"):
            score, analysis = genai.score_resume_against_jd(
                "Resume text",
                "Job description"
            )

            # Should fallback to text extraction or return 0
            assert isinstance(score, float)
            assert isinstance(analysis, str)

    def test_score_resume_against_jd_extracts_score_from_text(self):
        """score_resume_against_jd should extract score from non-JSON text"""
        with patch('genai.invoke_claude', return_value="The candidate scores 75 out of 100 points"):
            score, analysis = genai.score_resume_against_jd(
                "Resume text",
                "Job description"
            )

            assert score == 75.0


class TestMockScoring:
    """Test mock scoring functions (fallback when no AI backend)"""

    def test_mock_score_resume_returns_valid_score(self):
        """mock_score_resume should return score between 0-100"""
        resume_text = "Python developer with AWS experience"
        job_description = "Looking for Python and AWS skills"

        score, analysis = genai.mock_score_resume(resume_text, job_description)

        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert isinstance(analysis, str)

    def test_mock_score_resume_keyword_matching(self):
        """mock_score_resume should score based on keyword matches"""
        resume_high = "Python AWS ML AI Agent LLM Data Cloud API Automation"
        resume_low = "General office work and administration"
        job_desc = "Python AWS Agent LLM ML"

        score_high, _ = genai.mock_score_resume(resume_high, job_desc)
        score_low, _ = genai.mock_score_resume(resume_low, job_desc)

        # High keyword match should score higher
        assert score_high > score_low

    def test_mock_score_resume_analysis_includes_matches(self):
        """mock_score_resume analysis should mention keyword matches"""
        resume_text = "Python developer"
        job_description = "Python role"

        _, analysis = genai.mock_score_resume(resume_text, job_description)

        assert "match" in analysis.lower()


class TestNoteSummarization:
    """Test interview note summarization"""

    def test_smart_summarize_notes_returns_summary(self, mock_anthropic_client):
        """smart_summarize_notes should return summary text"""
        notes = "Candidate showed strong Python skills. Good communication. Needs more AWS experience."
        stage = "Technical Interview"

        summary = genai.smart_summarize_notes(notes, stage)

        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_smart_summarize_notes_handles_empty_notes(self):
        """smart_summarize_notes should handle empty notes"""
        summary = genai.smart_summarize_notes("", "Phone Screen")

        assert summary == "No notes to summarize"

    def test_mock_summarize_notes_returns_summary(self):
        """mock_summarize_notes should return mock summary"""
        notes = "Good candidate with strong technical skills"
        stage = "Technical Interview"

        summary = genai.mock_summarize_notes(notes, stage, "John Doe")

        assert isinstance(summary, str)
        assert stage in summary
        assert "[Mock Summary]" in summary or "Mock" in summary.lower()


class TestInterviewQuestionGeneration:
    """Test AI interview question generation"""

    def test_generate_interview_questions_returns_questions(self, mock_anthropic_client):
        """generate_interview_questions should return questions dict"""
        mock_response = Mock()
        mock_response.content = [Mock(
            text='{"questions": [{"question": "Tell me about Python", "category": "technical", '
                 '"probing_area": "Python skills"}], '
                 '"areas_to_probe": ["AWS experience"], "resume_concerns": []}'
        )]
        mock_anthropic_client.messages.create.return_value = mock_response

        with patch('genai.get_anthropic_client', return_value=mock_anthropic_client):
            result = genai.generate_interview_questions(
                job_description="Python developer",
                job_requirements="Python, AWS",
                resume_text="Python developer resume",
                stage="Technical Interview"
            )

            assert "questions" in result
            assert "areas_to_probe" in result
            assert "resume_concerns" in result
            assert isinstance(result["questions"], list)

    def test_generate_interview_questions_handles_missing_inputs(self):
        """generate_interview_questions should handle missing inputs"""
        result = genai.generate_interview_questions(
            job_description="",
            job_requirements="",
            resume_text="",
            stage="Technical Interview"
        )

        assert "questions" in result
        assert "areas_to_probe" in result
        assert len(result["questions"]) == 0

    def test_mock_generate_interview_questions_returns_stage_specific(self):
        """mock_generate_interview_questions should return stage-specific questions"""
        result_phone = genai.mock_generate_interview_questions(
            "Job desc", "Requirements", "Resume", "Phone Screen"
        )
        result_technical = genai.mock_generate_interview_questions(
            "Job desc", "Requirements", "Resume", "Technical Interview"
        )
        result_behavioral = genai.mock_generate_interview_questions(
            "Job desc", "Requirements", "Resume", "Behavioral Interview"
        )

        # Each stage should have questions
        assert len(result_phone["questions"]) > 0
        assert len(result_technical["questions"]) > 0
        assert len(result_behavioral["questions"]) > 0

        # Questions should be different for different stages
        assert result_phone["questions"][0] != result_technical["questions"][0]

    def test_smart_generate_interview_questions_respects_num_questions(self):
        """smart_generate_interview_questions should generate requested number of questions"""
        with patch('genai.ANTHROPIC_AVAILABLE', False):
            with patch('genai.BEDROCK_AVAILABLE', False):
                result = genai.smart_generate_interview_questions(
                    "Job desc", "Requirements", "Resume", "Technical Interview",
                    num_questions=5
                )

                assert len(result["questions"]) == 5


class TestCandidateComparison:
    """Test candidate comparison function"""

    def test_compare_candidates_handles_insufficient_candidates(self):
        """compare_candidates should handle less than 2 candidates"""
        result = genai.compare_candidates([], "Job description")

        assert result["recommendation"] is None
        assert "at least 2" in result["reasoning"].lower()

        result_one = genai.compare_candidates([{"name": "John"}], "Job description")
        assert result_one["recommendation"] is None

    def test_compare_candidates_returns_recommendation(self, mock_anthropic_client):
        """compare_candidates should return recommendation for multiple candidates"""
        candidates = [
            {
                "name": "John Doe",
                "current_stage": "Technical Interview",
                "days_in_pipeline": 5,
                "ai_resume_score": 85,
                "expected_hourly_rate": 100,
                "rate_status": "in_range",
                "total_interview_score": 90,
                "recommendations": 2,
                "strengths": ["Python", "AWS"],
                "gaps": []
            },
            {
                "name": "Jane Smith",
                "current_stage": "Phone Screen",
                "days_in_pipeline": 2,
                "ai_resume_score": 75,
                "expected_hourly_rate": 120,
                "rate_status": "above_range",
                "total_interview_score": 80,
                "recommendations": 1,
                "strengths": ["ML"],
                "gaps": ["Limited AWS"]
            }
        ]

        mock_response = Mock()
        mock_response.content = [Mock(
            text='{"recommendation": "John Doe", "reasoning": "Higher scores", '
                 '"comparison_summary": "John leads", "rankings": ["John Doe", "Jane Smith"]}'
        )]
        mock_anthropic_client.messages.create.return_value = mock_response

        with patch('genai.get_anthropic_client', return_value=mock_anthropic_client):
            result = genai.compare_candidates(candidates, "Python developer role")

            assert result["recommendation"] is not None
            assert "reasoning" in result
            assert "comparison_summary" in result
            assert "rankings" in result
            assert isinstance(result["rankings"], list)


class TestAIBackendStatus:
    """Test AI backend status reporting"""

    def test_get_ai_backend_status_returns_string(self):
        """get_ai_backend_status should return status string"""
        status = genai.get_ai_backend_status()

        assert isinstance(status, str)
        assert len(status) > 0

    def test_get_ai_backend_status_shows_mock_when_no_backend(self):
        """get_ai_backend_status should show Mock when no backend available"""
        with patch('genai.ANTHROPIC_AVAILABLE', False):
            with patch('genai.BEDROCK_AVAILABLE', False):
                status = genai.get_ai_backend_status()

                assert "Mock" in status or "mock" in status.lower()
