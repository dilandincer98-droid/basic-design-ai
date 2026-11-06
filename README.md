# Basic Design AI — Image-first Studio

An AI-assisted workspace for exploring **two-dimensional foundation design**. Built with **Python, Streamlit, and Google Gemini**, the application helps users interpret design assignments, develop composition ideas, generate black-and-white artwork, and critically review or revise their results.

The project focuses on **composition, geometric–organic relationships, linework, visual hierarchy, and negative space** rather than simply adding decorative detail.

> **Project status:** Active prototype. AI-generated critiques and scores are indicative, not official instructor assessments. Generated images should be reviewed by a human before academic use.

## What it does

- **Assignment analysis:** Extracts mandatory requirements, restrictions, and creative freedom from an instructor's brief.
- **Composition Concept Lab:** Proposes alternative composition strategies so a user can choose an artistic direction before generating an image.
- **Image generation:** Creates original visual studies from the assignment, selected concept, optional artistic direction, and an optional style reference.
- **Academic design review:** Assesses visible assignment compliance and provides strengths, problems, and suggested improvements.
- **Artistic reconstruction:** Explores more substantial changes to spatial organization and form relationships.
- **Technical refinement:** Focuses on improving detail, texture, readability, and line quality while retaining the main composition.
- **Image comparison and downloads:** Supports review of alternatives and saving work locally.

## Technology

- Python
- Streamlit
- Google Gemini API (`google-genai`)
- Pillow
- python-dotenv (for local development)

## Run locally

1. Clone the repository and open the project folder.
2. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Create a local `.env` file in the project root with your **own** Gemini API key:

   ```dotenv
   GEMINI_API_KEY=your_own_api_key_here
   ```

4. Start the app:

   ```bash
   python -m streamlit run app_ai_studio.py
   ```

**Important:** API requests can incur charges. Review current provider pricing, quotas, and billing limits before using generation or revision features.

## Security and usage costs

- The `.env` file and `.streamlit/secrets.toml` must never be committed to Git.
- This repository does **not** include a Gemini API key. Users running it locally must provide their own.
- **Do not deploy the application publicly with your personal API key powering unrestricted Generate, Analyze, Review, or Revise actions.** Visitors could trigger billable API requests.
- A public, read-only demo should disable all billable operations at the server level. A future interactive deployment would require secure authentication, per-user credentials or a different usage-control design.

## Project structure

```text
basic-design-ai/
├── app_ai_studio.py        # Streamlit interface
├── services/
│   └── studio_ai.py       # Gemini-backed analysis, generation, and review
├── requirements.txt
├── .gitignore
└── README.md
```

## Design principles

The studio distinguishes **teacher requirements** from **optional artistic direction**. It encourages users to evaluate whether geometric and organic forms create a coherent composition, whether the focal hierarchy is legible, and whether textures and negative space contribute meaningfully to the artwork.

## Limitations

Image generation is probabilistic, and a stronger prompt does not guarantee stronger design. AI reviews can be inconsistent and should not replace a qualified instructor's judgement. Digital images also cannot establish physical paper dimensions or print quality on their own.

## Author

**Dilan Dincer**

