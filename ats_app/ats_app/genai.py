"""
GenAI Functions - Resume Scoring & Note Summarization
Supports: Direct Anthropic API, AWS Bedrock, or mock for local testing
"""
import json
import logging
import os
import re
import threading
import time
from collections import deque
from typing import Dict, Optional, Tuple

from config import settings

# ---------------------------------------------------------------------------
# Prompt input length caps
# Prevents runaway token costs and keeps prompts within safe context limits.
# ---------------------------------------------------------------------------
MAX_PROMPT_INPUT_LENGTH_RESUME: int = 5000   # chars — resume text fields
MAX_PROMPT_INPUT_LENGTH_NOTES: int = 3000    # chars — notes / descriptions / JD fields

# ---------------------------------------------------------------------------
# In-process rate limiter for invoke_claude()
# Allows at most AI_RATE_LIMIT_MAX_CALLS calls per AI_RATE_LIMIT_WINDOW_SECONDS.
# ---------------------------------------------------------------------------
AI_RATE_LIMIT_MAX_CALLS: int = 20      # maximum calls per window
AI_RATE_LIMIT_WINDOW_SECONDS: int = 60  # sliding window length in seconds

_rate_limit_lock = threading.Lock()
_rate_limit_call_times: deque = deque()  # timestamps of recent invoke_claude() calls

logger = logging.getLogger(__name__)

# Try to import anthropic for direct API access
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Try to import boto3 for Bedrock
try:
    import boto3
    from botocore.config import Config as BotoConfig
    import botocore.exceptions
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False

def get_anthropic_client():
    """Get Anthropic client for direct API access"""
    if not ANTHROPIC_AVAILABLE:
        return None
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        return None
    try:
        return anthropic.Anthropic(api_key=api_key)
    except Exception:
        return None

def get_bedrock_client():
    """Get Bedrock runtime client"""
    if not BEDROCK_AVAILABLE:
        return None
    try:
        boto_config = BotoConfig(
            connect_timeout=settings.BEDROCK_CONNECT_TIMEOUT,
            read_timeout=settings.BEDROCK_READ_TIMEOUT
        )
        return boto3.client('bedrock-runtime', region_name=settings.AWS_REGION, config=boto_config)
    except Exception:
        return None

def invoke_claude_api(prompt: str, system: str = None, max_tokens: int = 1024) -> Optional[str]:
    """Invoke Claude via direct Anthropic API"""
    client = get_anthropic_client()
    if not client:
        logger.debug("invoke_claude_api: no client available")
        return None

    try:
        # Scale timeout with max_tokens — longer responses need more time
        timeout = max(settings.AI_TIMEOUT_SECONDS, max_tokens * 0.05)
        kwargs = {
            "model": settings.AI_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "timeout": timeout
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return response.content[0].text
    except anthropic.APIConnectionError as e:
        logger.error(f"Anthropic API connection failed: {e}")
        return None
    except anthropic.RateLimitError as e:
        logger.warning(f"Anthropic API rate limit exceeded: {e}")
        return None
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error in Anthropic API invocation: {e}")
        return None

def invoke_claude_bedrock(prompt: str, system: str = None, max_tokens: int = 1024) -> Optional[str]:
    """Invoke Claude via Bedrock"""
    client = get_bedrock_client()
    if not client:
        return None

    messages = [{"role": "user", "content": prompt}]

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages
    }
    if system:
        body["system"] = system

    try:
        response = client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps(body)
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except botocore.exceptions.ReadTimeoutError as e:
        logger.error(f"Bedrock read timeout: {e}")
        return None
    except botocore.exceptions.ClientError as e:
        logger.error(f"Bedrock client error: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response JSON: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error in Bedrock invocation: {e}")
        return None

def invoke_claude(prompt: str, system: str = None, max_tokens: int = 1024) -> Optional[str]:
    """Invoke Claude - tries direct API first, then Bedrock.

    Enforces an in-process sliding-window rate limit of
    AI_RATE_LIMIT_MAX_CALLS calls per AI_RATE_LIMIT_WINDOW_SECONDS.
    Returns None (without calling the API) when the limit is exceeded.
    """
    now = time.monotonic()
    with _rate_limit_lock:
        # Evict timestamps outside the current window
        cutoff = now - AI_RATE_LIMIT_WINDOW_SECONDS
        while _rate_limit_call_times and _rate_limit_call_times[0] <= cutoff:
            _rate_limit_call_times.popleft()

        if len(_rate_limit_call_times) >= AI_RATE_LIMIT_MAX_CALLS:
            logger.warning(
                "invoke_claude: rate limit reached (%d calls in the last %ds). "
                "Skipping AI call.",
                AI_RATE_LIMIT_MAX_CALLS,
                AI_RATE_LIMIT_WINDOW_SECONDS,
            )
            return None

        # Record this call before releasing the lock so concurrent threads
        # see it immediately.
        _rate_limit_call_times.append(now)

    # Try direct Anthropic API first (for local testing)
    result = invoke_claude_api(prompt, system, max_tokens)
    if result:
        return result

    # Fall back to Bedrock
    return invoke_claude_bedrock(prompt, system, max_tokens)

def score_resume_against_jd(resume_text: str, job_description: str, requirements: str = None) -> Tuple[float, str]:
    """
    Score a resume against a job description using Claude.
    Returns (score 0-100, analysis text)
    """
    if not resume_text or not job_description:
        return 0.0, "Missing resume or job description"

    # Truncate inputs to avoid excessive token usage
    if len(resume_text) > MAX_PROMPT_INPUT_LENGTH_RESUME:
        logger.debug(
            "score_resume_against_jd: resume_text truncated from %d to %d chars",
            len(resume_text), MAX_PROMPT_INPUT_LENGTH_RESUME,
        )
        resume_text = resume_text[:MAX_PROMPT_INPUT_LENGTH_RESUME]
    if len(job_description) > MAX_PROMPT_INPUT_LENGTH_NOTES:
        logger.debug(
            "score_resume_against_jd: job_description truncated from %d to %d chars",
            len(job_description), MAX_PROMPT_INPUT_LENGTH_NOTES,
        )
        job_description = job_description[:MAX_PROMPT_INPUT_LENGTH_NOTES]

    system = """You are an expert technical recruiter evaluating contractor resumes for agentic AI programs.
Be rigorous but fair. Focus on:
1. Direct skill matches to requirements
2. Relevant experience depth (not just keywords)
3. Evidence of hands-on work vs. theoretical knowledge
4. Red flags (gaps, job hopping, vague descriptions)

Output JSON only: {"score": <0-100>, "analysis": "<2-3 sentence summary>", "strengths": ["<strength>"], "gaps": ["<gap>"]}"""

    prompt = f"""Score this resume against the job requirements.

JOB DESCRIPTION:
{job_description}

{f"REQUIREMENTS:{chr(10)}{requirements}" if requirements else ""}

RESUME:
{resume_text}

Respond with JSON only."""

    response = invoke_claude(prompt, system)
    
    if response:
        try:
            # Try to parse JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get('score', 0))
                analysis = data.get('analysis', '')
                strengths = data.get('strengths', [])
                gaps = data.get('gaps', [])
                
                full_analysis = f"{analysis}\n\nStrengths: {', '.join(strengths)}\n\nGaps: {', '.join(gaps)}"
                return score, full_analysis
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI resume score JSON: {e}")
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid data in AI resume score response: {e}")
        
        # Fallback: try to extract score from text
        score_match = re.search(r'(\d{1,3})(?:\s*\/\s*100|\s*%|\s*points?)?', response)
        if score_match:
            score = min(100, float(score_match.group(1)))
            return score, response
    
    return 0.0, "AI scoring unavailable - manual review required"

def summarize_interview_notes(notes: str, stage: str, candidate_name: str = None) -> str:
    """
    Summarize interview notes to prepare for next stage.
    """
    if not notes:
        return "No notes to summarize"

    # Truncate notes to avoid excessive token usage
    if len(notes) > MAX_PROMPT_INPUT_LENGTH_NOTES:
        logger.debug(
            "summarize_interview_notes: notes truncated from %d to %d chars",
            len(notes), MAX_PROMPT_INPUT_LENGTH_NOTES,
        )
        notes = notes[:MAX_PROMPT_INPUT_LENGTH_NOTES]

    system = """You are preparing interview summaries for hiring managers.
Be concise, factual, and highlight:
1. Key strengths demonstrated
2. Concerns or areas to probe further
3. Overall recommendation (proceed/hold/reject)

Keep summaries under 150 words."""

    prompt = f"""Summarize these {stage} notes{f' for {candidate_name}' if candidate_name else ''}:

{notes}

Provide a brief summary for the next interviewer."""

    response = invoke_claude(prompt, system, max_tokens=300)
    
    if response:
        return response.strip()
    
    return "AI summary unavailable"

def generate_interview_prep(candidate_data: Dict, stage: str) -> str:
    """
    Generate interview prep notes with 8 technical and 3 behavioral questions.
    """
    system = """You are an expert technical interviewer preparing for a candidate interview.
Your output must be well-structured markdown with clear sections and numbered questions.
Each question should be tailored to the specific candidate and role based on the context provided."""

    # Build context from candidate data, truncating long fields to limit token usage
    context_parts = [f"Candidate: {candidate_data.get('name', 'Unknown')}"]
    context_parts.append(f"Role: {candidate_data.get('job_title', 'Not specified')}")

    if candidate_data.get('ai_resume_analysis'):
        analysis = candidate_data['ai_resume_analysis']
        if len(analysis) > MAX_PROMPT_INPUT_LENGTH_NOTES:
            logger.debug(
                "generate_interview_prep: ai_resume_analysis truncated from %d to %d chars",
                len(analysis), MAX_PROMPT_INPUT_LENGTH_NOTES,
            )
            analysis = analysis[:MAX_PROMPT_INPUT_LENGTH_NOTES]
        context_parts.append(f"Resume Analysis: {analysis}")

    if candidate_data.get('previous_notes'):
        prev_notes = candidate_data['previous_notes']
        if len(prev_notes) > MAX_PROMPT_INPUT_LENGTH_NOTES:
            logger.debug(
                "generate_interview_prep: previous_notes truncated from %d to %d chars",
                len(prev_notes), MAX_PROMPT_INPUT_LENGTH_NOTES,
            )
            prev_notes = prev_notes[:MAX_PROMPT_INPUT_LENGTH_NOTES]
        context_parts.append(f"Previous Interview Notes: {prev_notes}")

    prompt = f"""Prepare interview guidance for {stage}.

{chr(10).join(context_parts)}

Generate the following in markdown format:

## Key Areas to Explore
List 3-5 key areas the interviewer should focus on, based on the candidate's resume and role requirements.

## Technical Questions (8)
Generate exactly 8 technical interview questions relevant to the role and the candidate's background. For each question:
- Make it specific to the skills/technologies in the job and resume
- Include a brief note on what the question validates

## Behavioral Questions (3)
Generate exactly 3 behavioral interview questions using the STAR format prompt style. For each:
- Tie it to a competency relevant to the role
- Include what to look for in a strong answer

## Red Flags to Watch For
List 2-3 potential concerns to probe based on the resume analysis."""

    try:
        response = invoke_claude(prompt, system, max_tokens=4000)

        if response:
            return response.strip()

        logger.warning("generate_interview_prep: invoke_claude returned None")
        return "AI prep unavailable - review previous notes manually"
    except Exception as e:
        logger.exception(f"generate_interview_prep error: {e}")
        return f"AI prep error: {str(e)}"

def batch_rank_candidates(candidates: list, job_description: str) -> list:
    """
    Rank multiple candidates against a job description.
    Returns candidates with AI scores added.
    """
    ranked = []
    for candidate in candidates:
        if candidate.get('resume_text'):
            score, analysis = score_resume_against_jd(
                candidate['resume_text'],
                job_description
            )
            candidate['ai_resume_score'] = score
            candidate['ai_resume_analysis'] = analysis
        else:
            candidate['ai_resume_score'] = 0
            candidate['ai_resume_analysis'] = "No resume text available"
        ranked.append(candidate)
    
    # Sort by AI score descending
    ranked.sort(key=lambda x: x.get('ai_resume_score', 0), reverse=True)
    return ranked

# ============ MOCK FUNCTIONS FOR LOCAL TESTING ============
def mock_score_resume(resume_text: str, job_description: str, requirements: str = None) -> Tuple[float, str]:
    """Mock scoring for testing without Bedrock"""
    # Simple keyword matching for demo
    keywords = ['python', 'aws', 'agent', 'llm', 'ml', 'ai', 'data', 'cloud', 'api', 'automation']
    resume_lower = resume_text.lower()
    jd_lower = job_description.lower()
    
    matches = sum(1 for kw in keywords if kw in resume_lower and kw in jd_lower)
    score = min(100, matches * 12 + 20)  # Base score + keyword matches
    
    analysis = f"Mock Analysis: Found {matches} keyword matches. "
    if matches >= 5:
        analysis += "Strong alignment with role requirements."
    elif matches >= 3:
        analysis += "Moderate alignment - may need additional screening."
    else:
        analysis += "Limited keyword matches - review manually."
    
    return float(score), analysis

def mock_summarize_notes(notes: str, stage: str, candidate_name: str = None) -> str:
    """Mock summarization for testing"""
    word_count = len(notes.split())
    return f"[Mock Summary] {stage} notes ({word_count} words): Key points extracted from interview feedback. Recommend further discussion on technical depth."

# Use mock functions if no AI backend available
def smart_score_resume(resume_text: str, job_description: str, requirements: str = None) -> Tuple[float, str]:
    """Score resume using Claude API or Bedrock if available, mock otherwise"""
    if (ANTHROPIC_AVAILABLE and get_anthropic_client()) or (BEDROCK_AVAILABLE and get_bedrock_client()):
        return score_resume_against_jd(resume_text, job_description, requirements)
    return mock_score_resume(resume_text, job_description, requirements)

def smart_summarize_notes(notes: str, stage: str, candidate_name: str = None) -> str:
    """Summarize notes using Claude API or Bedrock if available, mock otherwise"""
    if (ANTHROPIC_AVAILABLE and get_anthropic_client()) or (BEDROCK_AVAILABLE and get_bedrock_client()):
        return summarize_interview_notes(notes, stage, candidate_name)
    return mock_summarize_notes(notes, stage, candidate_name)

def mock_generate_interview_prep(candidate_data: Dict, stage: str) -> str:
    """Mock interview prep generation for testing without AI backend."""
    name = candidate_data.get('name', 'the candidate')
    job_title = candidate_data.get('job_title', 'the role')
    analysis = candidate_data.get('ai_resume_analysis', '')

    prep = f"# Interview Guidance: {name} — {stage}\n\n"
    prep += f"**Role:** {job_title}\n\n"

    prep += "## Key Areas to Explore\n"
    prep += "1. Validate technical skills mentioned in resume against hands-on experience\n"
    prep += "2. Assess problem-solving approach with real-world scenarios\n"
    prep += "3. Evaluate communication skills and team collaboration style\n"
    prep += "4. Probe for specific project outcomes and measurable impact\n\n"

    if analysis:
        prep += f"> **Resume Analysis:** {analysis}\n\n"

    prep += "## Technical Questions (8)\n\n"
    prep += "1. **Walk me through the architecture of a system you built recently.** *Validates: system design skills*\n"
    prep += "2. **How would you approach debugging a performance issue in production?** *Validates: troubleshooting methodology*\n"
    prep += "3. **Describe your experience with the core technologies listed in the job description.** *Validates: technical depth*\n"
    prep += "4. **How do you ensure code quality and maintainability in your projects?** *Validates: engineering practices*\n"
    prep += "5. **Explain a complex technical concept you've worked with to a non-technical stakeholder.** *Validates: communication*\n"
    prep += "6. **What's your approach to testing — unit, integration, end-to-end?** *Validates: quality mindset*\n"
    prep += "7. **Describe a technical decision you made that you later had to revisit.** *Validates: judgment and adaptability*\n"
    prep += "8. **How do you stay current with new tools and technologies in your field?** *Validates: learning agility*\n\n"

    prep += "## Behavioral Questions (3)\n\n"
    prep += "1. **Tell me about a time you had to deliver results under tight deadlines. What was the situation, your approach, and the outcome?** *Competency: Execution under pressure. Look for: clear prioritization, communication with stakeholders.*\n"
    prep += "2. **Describe a situation where you disagreed with a team member on a technical approach. How did you handle it?** *Competency: Collaboration. Look for: respectful dialogue, data-driven resolution.*\n"
    prep += "3. **Give an example of when you identified a problem before anyone else noticed. What did you do?** *Competency: Ownership. Look for: proactive behavior, follow-through.*\n\n"

    prep += "## Red Flags to Watch For\n"
    prep += "- Vague answers without specific examples or measurable outcomes\n"
    prep += "- Inability to explain technical decisions or trade-offs clearly\n"
    prep += "- Gaps between resume claims and demonstrated depth in conversation\n"

    return prep

def smart_generate_interview_prep(candidate_data: Dict, stage: str) -> str:
    """Generate interview prep using Claude API or Bedrock if available, mock otherwise."""
    if (ANTHROPIC_AVAILABLE and get_anthropic_client()) or (BEDROCK_AVAILABLE and get_bedrock_client()):
        return generate_interview_prep(candidate_data, stage)
    return mock_generate_interview_prep(candidate_data, stage)

def extract_candidate_info(resume_text: str) -> Dict:
    """Extract structured candidate info from resume text using Claude."""
    system = """You are a resume parser. Extract the candidate's contact information from the resume text.
Output JSON only with these fields: {"name": "", "email": "", "phone": ""}
If a field cannot be found, use an empty string. Do not invent or guess information."""

    prompt = f"""Extract the candidate's name, email, and phone number from this resume:

{resume_text[:3000]}"""

    response = invoke_claude(prompt, system, max_tokens=200)
    if response:
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
    return {"name": "", "email": "", "phone": ""}


def mock_extract_candidate_info(resume_text: str) -> Dict:
    """Extract candidate info using regex when no AI backend is available."""
    result = {"name": "", "email": "", "phone": ""}

    # Extract email
    email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', resume_text)
    if email_match:
        result["email"] = email_match.group()

    # Extract phone
    phone_match = re.search(r'[\(]?\d{3}[\)]?[\s.\-]?\d{3}[\s.\-]?\d{4}', resume_text)
    if phone_match:
        result["phone"] = phone_match.group()

    # Extract name - use first non-empty line as best guess
    for line in resume_text.split('\n'):
        line = line.strip()
        if line and not re.match(r'^[\w.+-]+@', line) and not re.match(r'^[\(]?\d{3}', line):
            # Take first meaningful line, strip common suffixes
            name = re.sub(r'\s*[-–|,].*$', '', line).strip()
            if len(name) > 1 and len(name) < 60:
                result["name"] = name
                break

    return result


def smart_extract_candidate_info(resume_text: str) -> Dict:
    """Extract candidate info using Claude if available, regex fallback otherwise."""
    if (ANTHROPIC_AVAILABLE and get_anthropic_client()) or (BEDROCK_AVAILABLE and get_bedrock_client()):
        return extract_candidate_info(resume_text)
    return mock_extract_candidate_info(resume_text)


def get_ai_backend_status() -> str:
    """Return which AI backend is currently active"""
    if ANTHROPIC_AVAILABLE and get_anthropic_client():
        return "Claude API (Direct)"
    elif BEDROCK_AVAILABLE and get_bedrock_client():
        return "AWS Bedrock"
    else:
        return "Mock (No AI backend configured)"


def compare_candidates(candidates: list, job_description: str) -> dict:
    """
    Compare candidates and provide AI-powered recommendation.

    Args:
        candidates: List of candidate dicts with comparison data
        job_description: The job description text

    Returns:
        dict with:
            'recommendation': str (candidate name),
            'reasoning': str (detailed reasoning),
            'comparison_summary': str (brief summary),
            'rankings': list (ordered list of candidate names with scores)
    """
    if not candidates or len(candidates) < 2:
        return {
            'recommendation': None,
            'reasoning': 'Need at least 2 candidates to compare',
            'comparison_summary': 'Insufficient candidates for comparison',
            'rankings': []
        }

    # Build candidate summaries for the prompt
    candidate_summaries = []
    for i, c in enumerate(candidates):
        summary = f"""
CANDIDATE {i+1}: {c.get('name', 'Unknown')}
- Current Stage: {c.get('current_stage', 'N/A')}
- Days in Pipeline: {c.get('days_in_pipeline') or 0}
- AI Resume Score: {(c.get('ai_resume_score') or 0):.0f}%
- Expected Rate: ${(c.get('expected_hourly_rate') or 0):.0f}/hr (Status: {c.get('rate_status', 'unknown')})
- Interview Score: {(c.get('total_interview_score') or 0):.0f}%
- Recommendations Received: {c.get('recommendations') or 0}
- Strengths: {', '.join(c.get('strengths') or []) or 'Not analyzed'}
- Gaps: {', '.join(c.get('gaps') or []) or 'None identified'}
"""
        candidate_summaries.append(summary)

    system = """You are an expert technical recruiter helping compare candidates for a role.
Provide a clear, actionable recommendation on the strongest candidate.
Be objective and base your assessment on the data provided.

Output JSON only:
{
    "recommendation": "<name of recommended candidate>",
    "reasoning": "<2-3 sentences explaining why this candidate is the best fit>",
    "comparison_summary": "<1 sentence summary comparing all candidates>",
    "rankings": ["<1st place name>", "<2nd place name>", "<3rd place name if applicable>"]
}"""

    prompt = f"""Compare these candidates for the following role and recommend the strongest one.

JOB DESCRIPTION:
{job_description}

CANDIDATES:
{''.join(candidate_summaries)}

Consider:
1. AI resume scores (technical fit)
2. Interview performance
3. Compensation fit (rate within range)
4. Pipeline progress and momentum
5. Identified strengths vs gaps

Respond with JSON only."""

    response = invoke_claude(prompt, system, max_tokens=500)

    if response:
        try:
            # Try to parse JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    'recommendation': data.get('recommendation', candidates[0].get('name')),
                    'reasoning': data.get('reasoning', 'AI analysis completed'),
                    'comparison_summary': data.get('comparison_summary', 'Comparison complete'),
                    'rankings': data.get('rankings', [c.get('name') for c in candidates])
                }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse candidate comparison JSON: {e}")
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid data in candidate comparison response: {e}")

    # Fallback: simple score-based ranking
    sorted_candidates = sorted(candidates, key=lambda x: (
        x.get('ai_resume_score', 0) * 0.4 +
        x.get('total_interview_score', 0) * 0.4 +
        (20 if x.get('rate_status') == 'in_range' else 0)
    ), reverse=True)

    top = sorted_candidates[0]
    return {
        'recommendation': top.get('name', 'Unknown'),
        'reasoning': f"Based on available data, {top.get('name')} has the strongest combination of AI resume score ({top.get('ai_resume_score', 0):.0f}%) and interview performance ({top.get('total_interview_score', 0):.0f}%).",
        'comparison_summary': f"Compared {len(candidates)} candidates based on resume fit, interview scores, and compensation alignment.",
        'rankings': [c.get('name', 'Unknown') for c in sorted_candidates]
    }


def generate_interview_questions(
    job_description: str,
    job_requirements: str,
    resume_text: str,
    stage: str,
    previous_feedback: str = None,
    num_questions: int = 8
) -> dict:
    """
    Generate tailored interview questions using Claude.

    Args:
        job_description: The job description text
        job_requirements: Specific requirements for the role
        resume_text: The candidate's resume text
        stage: Interview stage (phone screen, technical, behavioral)
        previous_feedback: Notes/feedback from previous interview stages
        num_questions: Number of questions to generate (default 8)

    Returns: {
        'questions': [{'question': str, 'category': str, 'probing_area': str}],
        'areas_to_probe': [str],
        'resume_concerns': [str]
    }
    """
    if not job_description or not resume_text:
        return {
            'questions': [],
            'areas_to_probe': ['Unable to generate - missing job description or resume'],
            'resume_concerns': []
        }

    # Truncate long inputs to limit token usage
    if len(resume_text) > MAX_PROMPT_INPUT_LENGTH_RESUME:
        logger.debug(
            "generate_interview_questions: resume_text truncated from %d to %d chars",
            len(resume_text), MAX_PROMPT_INPUT_LENGTH_RESUME,
        )
        resume_text = resume_text[:MAX_PROMPT_INPUT_LENGTH_RESUME]
    if len(job_description) > MAX_PROMPT_INPUT_LENGTH_NOTES:
        logger.debug(
            "generate_interview_questions: job_description truncated from %d to %d chars",
            len(job_description), MAX_PROMPT_INPUT_LENGTH_NOTES,
        )
        job_description = job_description[:MAX_PROMPT_INPUT_LENGTH_NOTES]
    if previous_feedback and len(previous_feedback) > MAX_PROMPT_INPUT_LENGTH_NOTES:
        logger.debug(
            "generate_interview_questions: previous_feedback truncated from %d to %d chars",
            len(previous_feedback), MAX_PROMPT_INPUT_LENGTH_NOTES,
        )
        previous_feedback = previous_feedback[:MAX_PROMPT_INPUT_LENGTH_NOTES]

    # Define stage-specific guidance
    stage_guidance = {
        'Phone Screen': """Focus on:
- Culture fit and motivation questions
- Basic qualification verification
- Communication skills assessment
- High-level experience validation
- Salary expectations and availability
Question style: Open-ended, conversational, assessing fit and basic qualifications.""",

        'Technical Interview': """Focus on:
- Deep technical skill assessment aligned with job requirements
- Problem-solving approach and methodology
- Hands-on experience validation (ask for specific examples)
- System design or architecture questions if senior role
- Code/technical scenario questions
Question style: Technical depth, ask for specific examples, validate claimed expertise.""",

        'Behavioral Interview': """Focus on:
- STAR format questions (Situation, Task, Action, Result)
- Leadership and teamwork examples
- Conflict resolution and communication
- Adaptability and learning agility
- Past project outcomes and learnings
Question style: Behavioral STAR questions requiring specific past examples."""
    }

    stage_focus = stage_guidance.get(stage, stage_guidance['Technical Interview'])

    system = f"""You are an expert technical interviewer preparing interview questions for an agentic AI program hiring contractors.

Your task is to generate tailored interview questions based on:
1. The job description and requirements
2. The candidate's resume
3. The interview stage: {stage}
4. Any previous interview feedback

{stage_focus}

IMPORTANT ANALYSIS TASKS:
1. Identify resume gaps or concerns:
   - Employment gaps (periods without work)
   - Job hopping (short tenures < 1 year)
   - Vague descriptions lacking specifics
   - Skills claimed but not demonstrated with examples
   - Misalignment between claimed experience and job requirements
   - Buzzword-heavy descriptions without substance

2. Identify areas to probe deeper:
   - Skills critical to the role that need validation
   - Experiences that seem exaggerated or unclear
   - Transitions that need explanation
   - Projects mentioned without clear outcomes

Generate exactly {num_questions} questions.

Output ONLY valid JSON in this exact format:
{{
    "questions": [
        {{
            "question": "The interview question text",
            "category": "technical|behavioral|situational|experience|culture_fit",
            "probing_area": "What this question aims to validate or explore"
        }}
    ],
    "areas_to_probe": ["Area 1 to explore further", "Area 2 to explore further"],
    "resume_concerns": ["Concern 1 about the resume", "Concern 2 about the resume"]
}}"""

    prompt = f"""Generate interview questions for this candidate.

JOB DESCRIPTION:
{job_description}

{f"REQUIREMENTS:{chr(10)}{job_requirements}" if job_requirements else ""}

CANDIDATE RESUME:
{resume_text}

{f"PREVIOUS INTERVIEW FEEDBACK:{chr(10)}{previous_feedback}" if previous_feedback else ""}

INTERVIEW STAGE: {stage}

Generate {num_questions} tailored questions. Output JSON only."""

    response = invoke_claude(prompt, system, max_tokens=2000)

    if response:
        try:
            # Try to parse JSON from response
            # Handle potential markdown code blocks
            json_text = response
            if '```json' in response:
                json_text = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                json_text = response.split('```')[1].split('```')[0]

            # Find JSON object in response
            json_match = re.search(r'\{[\s\S]*\}', json_text)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    'questions': data.get('questions', []),
                    'areas_to_probe': data.get('areas_to_probe', []),
                    'resume_concerns': data.get('resume_concerns', [])
                }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse interview questions JSON: {e}")
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid data in interview questions response: {e}")

    # Fallback if AI unavailable or parsing fails
    return mock_generate_interview_questions(job_description, job_requirements, resume_text, stage, num_questions)


def mock_generate_interview_questions(
    job_description: str,
    job_requirements: str,
    resume_text: str,
    stage: str,
    num_questions: int = 8
) -> dict:
    """Mock question generation for testing without AI backend."""

    # Stage-specific mock questions
    mock_questions = {
        'Phone Screen': [
            {"question": "Tell me about yourself and what drew you to this role?", "category": "culture_fit", "probing_area": "Motivation and communication skills"},
            {"question": "Walk me through your most recent project and your specific contributions.", "category": "experience", "probing_area": "Recent experience relevance"},
            {"question": "What are your salary expectations and availability to start?", "category": "situational", "probing_area": "Logistics and expectations alignment"},
            {"question": "Why are you looking to leave your current position?", "category": "culture_fit", "probing_area": "Career motivations and red flags"},
            {"question": "How do you stay current with technology trends in your field?", "category": "behavioral", "probing_area": "Learning agility and initiative"},
            {"question": "Describe your ideal work environment and team structure.", "category": "culture_fit", "probing_area": "Cultural fit assessment"},
            {"question": "What do you know about our agentic AI programs?", "category": "culture_fit", "probing_area": "Research and genuine interest"},
            {"question": "What questions do you have about the role or team?", "category": "culture_fit", "probing_area": "Engagement and curiosity"},
        ],
        'Technical Interview': [
            {"question": "Describe a complex technical problem you solved recently. What was your approach?", "category": "technical", "probing_area": "Problem-solving methodology"},
            {"question": "How would you design a system to handle [relevant technical scenario]?", "category": "technical", "probing_area": "System design skills"},
            {"question": "Walk me through your experience with the technologies mentioned in your resume.", "category": "technical", "probing_area": "Technical depth validation"},
            {"question": "Describe a time you had to learn a new technology quickly. How did you approach it?", "category": "behavioral", "probing_area": "Learning agility"},
            {"question": "How do you ensure code quality and maintainability in your projects?", "category": "technical", "probing_area": "Engineering practices"},
            {"question": "Tell me about a technical decision you made that you later had to revisit.", "category": "technical", "probing_area": "Technical judgment and adaptability"},
            {"question": "How do you approach debugging a complex issue in production?", "category": "technical", "probing_area": "Troubleshooting skills"},
            {"question": "Describe your experience with AI/ML systems or agentic workflows.", "category": "technical", "probing_area": "Domain-specific expertise"},
        ],
        'Behavioral Interview': [
            {"question": "Tell me about a time you had a conflict with a team member. How did you resolve it?", "category": "behavioral", "probing_area": "Conflict resolution skills"},
            {"question": "Describe a project that failed or didn't meet expectations. What did you learn?", "category": "behavioral", "probing_area": "Accountability and learning"},
            {"question": "Give an example of when you had to influence others without direct authority.", "category": "behavioral", "probing_area": "Leadership and influence"},
            {"question": "Tell me about a time you had to deliver results under tight deadlines.", "category": "behavioral", "probing_area": "Performance under pressure"},
            {"question": "Describe a situation where you received critical feedback. How did you respond?", "category": "behavioral", "probing_area": "Receptiveness to feedback"},
            {"question": "Give an example of when you went above and beyond for a project or customer.", "category": "behavioral", "probing_area": "Initiative and ownership"},
            {"question": "Tell me about a time you had to adapt to a significant change at work.", "category": "behavioral", "probing_area": "Adaptability"},
            {"question": "Describe your approach to mentoring or helping junior team members.", "category": "behavioral", "probing_area": "Collaboration and mentorship"},
        ]
    }

    questions = mock_questions.get(stage, mock_questions['Technical Interview'])[:num_questions]

    return {
        'questions': questions,
        'areas_to_probe': [
            "[Mock] Validate specific technical skills mentioned in resume",
            "[Mock] Explore career transitions and gaps if any",
            "[Mock] Assess cultural fit for team environment"
        ],
        'resume_concerns': [
            "[Mock] AI analysis unavailable - manual review recommended",
            "[Mock] Verify specific project outcomes and metrics"
        ]
    }


def smart_generate_interview_questions(
    job_description: str,
    job_requirements: str,
    resume_text: str,
    stage: str,
    previous_feedback: str = None,
    num_questions: int = 8
) -> dict:
    """Generate interview questions using Claude API or Bedrock if available, mock otherwise."""
    if (ANTHROPIC_AVAILABLE and get_anthropic_client()) or (BEDROCK_AVAILABLE and get_bedrock_client()):
        return generate_interview_questions(
            job_description, job_requirements, resume_text,
            stage, previous_feedback, num_questions
        )
    return mock_generate_interview_questions(
        job_description, job_requirements, resume_text,
        stage, num_questions
    )


def comparative_resume_analysis(candidates: list, job: dict) -> str:
    """
    Generate a comparative analysis of candidates based purely on resume merit
    relative to the job description. Does NOT factor in interview performance.

    Args:
        candidates: List of candidate dicts with name, resume_text, ai_resume_score, ai_resume_analysis
        job: Job dict with title, description, requirements

    Returns:
        Markdown-formatted comparative analysis report
    """
    candidate_blocks = []
    for i, c in enumerate(candidates):
        # Truncate resume text and analysis to limit token usage per candidate
        resume_excerpt = (c.get('resume_text') or '')[:MAX_PROMPT_INPUT_LENGTH_RESUME]
        raw_analysis = c.get('ai_resume_analysis') or 'No AI analysis available'
        analysis = raw_analysis[:MAX_PROMPT_INPUT_LENGTH_NOTES]
        if len(raw_analysis) > MAX_PROMPT_INPUT_LENGTH_NOTES:
            logger.debug(
                "comparative_resume_analysis: ai_resume_analysis for candidate %d "
                "truncated from %d to %d chars",
                i + 1, len(raw_analysis), MAX_PROMPT_INPUT_LENGTH_NOTES,
            )
        score = c.get('ai_resume_score', 0) or 0
        candidate_blocks.append(
            f"CANDIDATE {i+1}: {c.get('name', 'Unknown')}\n"
            f"- AI Resume Score: {score:.0f}%\n"
            f"- AI Analysis: {analysis}\n"
            f"- Resume Excerpt:\n{resume_excerpt}\n"
        )

    system = """You are an expert technical recruiter performing a comparative resume analysis.
You are comparing candidates SOLELY on the merit of their resumes relative to the job description.
You must NOT reference interview performance, interviewer feedback, or any data beyond the resumes and job description.

Produce a well-structured markdown report with these sections:

## Candidate Profiles
For each candidate, summarize their key qualifications, relevant experience, and notable skills as they relate to the job.

## Side-by-Side Comparison
A comparison across these dimensions:
- Technical skills alignment with job requirements
- Depth and relevance of experience
- Education and certifications
- Domain expertise fit

## Strengths & Gaps per Candidate
For each candidate, list their top strengths and any gaps relative to the job requirements.

## Ranking & Rationale
Rank candidates from strongest to weakest resume fit, with clear reasoning for each placement.

Be specific, reference actual resume content, and keep the analysis objective."""

    prompt = f"""Perform a comparative resume analysis for the following job and candidates.

JOB: {job.get('title', 'Unknown Position')}

JOB DESCRIPTION:
{job.get('description', 'No description provided')}

JOB REQUIREMENTS:
{job.get('requirements', 'No requirements provided')}

{chr(10).join(candidate_blocks)}

Generate the full comparative analysis report in markdown."""

    try:
        response = invoke_claude(prompt, system, max_tokens=4000)
        if response:
            return response.strip()
        logger.warning("comparative_resume_analysis: invoke_claude returned None")
        return mock_comparative_resume_analysis(candidates, job)
    except Exception as e:
        logger.exception(f"comparative_resume_analysis error: {e}")
        return mock_comparative_resume_analysis(candidates, job)


def mock_comparative_resume_analysis(candidates: list, job: dict) -> str:
    """Fallback comparative analysis when no AI backend is available."""
    sorted_candidates = sorted(
        candidates,
        key=lambda c: c.get('ai_resume_score', 0) or 0,
        reverse=True
    )

    report = f"# Comparative Resume Analysis\n\n"
    report += f"**Position:** {job.get('title', 'Unknown')}\n\n"

    report += "## Candidate Profiles\n\n"
    for c in sorted_candidates:
        score = c.get('ai_resume_score', 0) or 0
        analysis = c.get('ai_resume_analysis') or 'No analysis available'
        report += f"### {c.get('name', 'Unknown')}\n"
        report += f"- **AI Resume Score:** {score:.0f}%\n"
        report += f"- **Analysis:** {analysis}\n\n"

    report += "## Ranking & Rationale\n\n"
    for rank, c in enumerate(sorted_candidates, 1):
        score = c.get('ai_resume_score', 0) or 0
        report += f"{rank}. **{c.get('name', 'Unknown')}** — AI Resume Score: {score:.0f}%\n"

    report += "\n*Note: This ranking is based on AI resume scores only. "
    report += "A full AI analysis was not available at the time of generation.*\n"

    return report


def smart_comparative_resume_analysis(candidates: list, job: dict) -> str:
    """Generate comparative resume analysis using Claude if available, mock fallback otherwise."""
    if (ANTHROPIC_AVAILABLE and get_anthropic_client()) or (BEDROCK_AVAILABLE and get_bedrock_client()):
        return comparative_resume_analysis(candidates, job)
    return mock_comparative_resume_analysis(candidates, job)
