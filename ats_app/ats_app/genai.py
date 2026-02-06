"""
GenAI Functions - Resume Scoring & Note Summarization
Supports: Direct Anthropic API, AWS Bedrock, or mock for local testing
"""
import json
import logging
import os
import re
from typing import Dict, Optional, Tuple

from config import settings

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
        return None

    try:
        kwargs = {
            "model": settings.AI_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "timeout": settings.AI_TIMEOUT_SECONDS
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
    """Invoke Claude - tries direct API first, then Bedrock"""
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
    Generate interview prep notes based on previous stages.
    """
    system = """You are helping interviewers prepare for candidate interviews.
Based on previous stage feedback, suggest:
1. Key areas to explore
2. Specific questions to ask
3. What to validate from previous feedback

Be concise and actionable."""

    # Build context from candidate data
    context_parts = [f"Candidate: {candidate_data.get('name', 'Unknown')}"]
    context_parts.append(f"Role: {candidate_data.get('job_title', 'Not specified')}")
    
    if candidate_data.get('ai_resume_analysis'):
        context_parts.append(f"Resume Analysis: {candidate_data['ai_resume_analysis']}")
    
    if candidate_data.get('previous_notes'):
        context_parts.append(f"Previous Interview Notes: {candidate_data['previous_notes']}")
    
    prompt = f"""Prepare interview guidance for {stage}.

{chr(10).join(context_parts)}

Provide 3-5 specific areas to explore and questions to ask."""

    response = invoke_claude(prompt, system, max_tokens=500)
    
    if response:
        return response.strip()
    
    return "AI prep unavailable - review previous notes manually"

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
- Days in Pipeline: {c.get('days_in_pipeline', 0)}
- AI Resume Score: {c.get('ai_resume_score', 0):.0f}%
- Expected Rate: ${c.get('expected_hourly_rate', 0):.0f}/hr (Status: {c.get('rate_status', 'unknown')})
- Interview Score: {c.get('total_interview_score', 0):.0f}%
- Recommendations Received: {c.get('recommendations', 0)}
- Strengths: {', '.join(c.get('strengths', [])) or 'Not analyzed'}
- Gaps: {', '.join(c.get('gaps', [])) or 'None identified'}
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
