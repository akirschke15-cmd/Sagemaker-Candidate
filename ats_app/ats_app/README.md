# Agentic Program ATS

Applicant Tracking System for managing contractor hiring pipelines.

## Features

- **Full Lifecycle Tracking**: Resume Screen → Phone Screen → Technical → Behavioral → Offer → Hired/Rejected
- **Custom Scoring**: Define criteria per role per stage with weighted scoring
- **AI-Powered Analysis**: Resume-to-JD matching, note summarization (requires Bedrock access)
- **Vendor Management**: Track performance by staffing agency
- **Interview Scheduling**: Schedule with email templates
- **Analytics & Export**: Pipeline stats, vendor performance, CSV export

## DSCP SageMaker Deployment

### 1. Upload Files

Upload the following to your SageMaker notebook (e.g., `/home/ec2-user/SageMaker/ats_app/`):
- `app.py` (main application)
- `database.py` (data layer)
- `genai.py` (AI functions)
- `email_utils.py` (email utilities)
- `requirements.txt`

### 2. Install Dependencies

```bash
cd /home/ec2-user/SageMaker/ats_app

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install from internal Nexus
pip install -r requirements.txt \
  --index-url https://nexus-tools.swacorp.com/repository/pypi-all/simple \
  --trusted-host nexus-tools.swacorp.com \
  --prefer-binary
```

### 3. Launch Application

```bash
streamlit run app.py --server.address=0.0.0.0 --server.baseUrlPath="/proxy/absolute/8501"
```

### 4. Access

1. Copy your Jupyter Notebook URL
2. Remove `/tree/...` from the URL
3. Append `/proxy/absolute/8501/`

Example:
```
https://your-notebook.notebook.us-east-1.sagemaker.aws/proxy/absolute/8501/
```

## Bedrock Configuration

The app uses Claude via AWS Bedrock for AI features. On DSCP, this should work automatically if your SageMaker role has Bedrock permissions.

If AI features show "unavailable", verify:
1. Bedrock is enabled in your region
2. Your IAM role has `bedrock:InvokeModel` permission
3. The model ID in `genai.py` matches your available models

### Available Model IDs
```python
# Adjust in genai.py if needed:
modelId="anthropic.claude-3-sonnet-20240229-v1:0"
# or
modelId="anthropic.claude-3-haiku-20240307-v1:0"
```

## Data Persistence

SQLite database (`ats_data.db`) is created in the app directory. For DSCP:
- Data persists as long as the notebook instance exists
- Back up regularly by copying `ats_data.db`
- For multi-user access, consider migrating to RDS

## Customization

### Adding Scoring Criteria
1. Go to Jobs → Select a Job → Scoring Criteria
2. Add criteria for each interview stage
3. Set max score and weight

### Email Templates
Pre-built templates exist for:
- Phone Screen Invite
- Technical Interview Invite
- Rejection
- Offer

SMTP is required for actual sending. Set environment variables:
```bash
export SMTP_HOST=your.smtp.server
export SMTP_USER=your_user
export SMTP_PASSWORD=your_password
```

## Architecture

```
ats_app/
├── app.py           # Streamlit UI (800+ lines)
├── database.py      # SQLite models & queries
├── genai.py         # Bedrock integration
├── email_utils.py   # Email rendering & sending
├── requirements.txt # Dependencies
└── ats_data.db      # SQLite database (auto-created)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8501 in use | Change port: `--server.port=8502` and update URL path |
| AI features unavailable | Check Bedrock permissions and region |
| Database locked | Restart the Streamlit process |
| Slow initial load | First run installs npm packages; subsequent loads are faster |
