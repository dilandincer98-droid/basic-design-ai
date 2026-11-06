"""Gemini tools for Basic Design AI Image-first Studio.

Keep the teacher brief authoritative and the artistic preferences optional.
"""
import io
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

TEXT_MODEL = os.getenv('GEMINI_TEXT_MODEL', 'gemini-3-flash-preview')
IMAGE_MODEL = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-3.1-flash-image')
VALID_IMAGE_MODELS = {'gemini-3.1-flash-image', 'gemini-3-pro-image'}
VALID_SIZES = {'1K', '2K', '4K'}


def client():
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY missing from the project .env file')
    return genai.Client(api_key=key)


def png_bytes(raw):
    with Image.open(io.BytesIO(raw)) as im:
        out = io.BytesIO()
        im.convert('RGB').save(out, format='PNG')
        return out.getvalue()


def image_part(raw):
    with Image.open(io.BytesIO(raw)) as im:
        im = im.convert('RGB')
        im.thumbnail((1800, 1800))
        out = io.BytesIO()
        im.save(out, format='PNG')
    return types.Part.from_bytes(data=out.getvalue(), mime_type='image/png')


def extract_image(response):
    for candidate in response.candidates or []:
        if candidate.content is None:
            continue
        for part in candidate.content.parts or []:
            inline = getattr(part, 'inline_data', None)
            if inline is not None and inline.data:
                return png_bytes(inline.data)
    raise RuntimeError('Gemini returned no image. Check model access, response, and billing.')


def parse_json(text):
    clean = (text or '').strip()
    if clean.startswith('```'):
        clean = clean.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    if not clean:
        raise RuntimeError('Gemini returned an empty JSON response')
    return json.loads(clean)


def analyze(brief):
    instructions = '''Analyze ONLY the teacher's actual assignment. Do not invent requirements.
Return a JSON object with these exact keys: summary (string), mandatory (array of strings), forbidden
(array of strings), uncertain (array of strings), design_principles (array of strings),
artistic_freedom (array of strings). Separate required constraints from optional artistic decisions.
Do not claim physical paper measurements can be verified from a digital image.
Respond in Turkish, as strict JSON without markdown.'''
    with client() as gemini_client:
        response = gemini_client.models.generate_content(
            model=TEXT_MODEL,
            contents=f'{instructions}\n\nTEACHER ASSIGNMENT:\n{brief}',
            config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0),
        )
        return parse_json(response.text)



def propose_concepts(brief, analysis, direction=""):
    """Generate three distinct composition plans, no image is produced."""
    if not brief.strip():
        raise ValueError("Teacher assignment is required.")
    instructions = """You are a demanding foundation-design art director.
Develop exactly THREE genuinely DIFFERENT, original, feasible composition concepts for the teacher's brief.
Do not draw images. Do not claim you have examined an image. Never invent mandatory requirements.
For each concept define an explicit structural idea, a clear spatial layout, focal transformation,
figure-ground/negative-space strategy, line texture plan, and potential weaknesses.
The three concepts must NOT be trivial variations of the same layout: different silhouette,
movement path and organization of geometry. Favor meaningful formal relationships over decorative detail.
Do not simply repeat typical clusters of little squares connected to endless wavy ribbons.
Return only a JSON object with key 'concepts' containing exactly 3 objects. Each object must have
keys 'title', 'idea', 'layout', 'focal_transformation', 'negative_space', 'texture_strategy',
'originality_rationale', 'risks', 'visual_prompt'. Each field must be a nonempty string.
'visual_prompt' is a precise English instruction paragraph describing concrete placement and
transformation choices, for use within an image generation prompt. Write other fields in Turkish.
Never promise a perfect result. The teacher brief remains authoritative."""
    content = (f"{instructions}\n\nTEACHER BRIEF:\n{brief}\n\n"
               f"ASSIGNMENT ANALYSIS:\n{json.dumps(analysis, ensure_ascii=False)}\n\n"
               f"OPTIONAL STUDENT ART DIRECTION:\n{direction}")
    with client() as gemini_client:
        response = gemini_client.models.generate_content(
            model=TEXT_MODEL,
            contents=content,
            config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0.75),
        )
        data = parse_json(response.text)
    concepts = data.get('concepts')
    fields = ('title', 'idea', 'layout', 'focal_transformation', 'negative_space',
              'texture_strategy', 'originality_rationale', 'risks', 'visual_prompt')
    if not isinstance(concepts, list) or len(concepts) != 3:
        raise ValueError('Concept Lab expected exactly three concepts. No images were charged or generated.')
    for item in concepts:
        if not isinstance(item, dict) or any(not isinstance(item.get(f), str) or not item[f].strip() for f in fields):
            raise ValueError('Concept Lab received incomplete concept data. No image was generated.')
    return concepts


def create_prompt(brief, analysis, direction):
    artistic_direction = (direction or '').strip() or (
        'Geometric Metamorphosis: develop one unified composition in which '
        'square-derived structures transform into expressive organic movement.'
    )
    return f'''Create ONE original, visually compelling foundation-design artwork.
Artistic coherence matters more than decorative complexity.

1. TEACHER ASSIGNMENT — MANDATORY
{brief}

The teacher's requirements override all artistic preferences below. Do not invent constraints.

2. CENTRAL ARTISTIC CONCEPT — OPTIONAL
{artistic_direction}

Choose ONE distinctive organizing idea. Do not turn the brief into a checklist of unrelated motifs.

3. COMPOSITIONAL INTELLIGENCE
Establish one dominant geometric-organic relationship and a legible visual hierarchy.
Use connected supporting forms, controlled asymmetry, and active negative space.
Avoid separately decorated square cells, repeated floating icons, and monotonous pattern filling.

4. FORM INTEGRATION
Where relevant to the teacher's assignment, organic contours should emerge from,
transform, or share boundaries with square-derived geometry, rather than simply overlay it.
Use transformations selectively so the structural relationships remain legible.

5. INK CRAFT AND VISUAL RHYTHM
Use deliberate line weights, precise boundaries, selected hatching, and intentional black-white contrasts.
Do not confuse visual sophistication with excessive line density or tangled intersections.
Preserve calm regions and readable figure-ground relationships.

6. ORIGINALITY
Any supplied style reference is for craftsmanship and general visual sophistication ONLY.
Create an original arrangement; do not copy distinctive forms or the reference layout.

7. INTERNAL QUALITY CHECK
Before returning the image, prefer coherent structure, original visual identity,
meaningful negative spaces, purposeful textures, and adherence to the teacher's brief.

FINAL OUTPUT: One finished artwork, without labels, captions, or presentation mockups.'''


def generate(prompt, reference=None, model=None, image_size='2K'):
    chosen_model = model or IMAGE_MODEL
    if chosen_model not in VALID_IMAGE_MODELS:
        raise ValueError(f'Unsupported image model: {chosen_model}')
    if image_size not in VALID_SIZES:
        raise ValueError(f'Unsupported image size: {image_size}')
    parts = [types.Part.from_text(text=prompt)]
    if reference is not None:
        parts.append(image_part(reference))
    with client() as gemini_client:
        response = gemini_client.models.generate_content(
            model=chosen_model,
            contents=types.Content(role='user', parts=parts),
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
                image_config=types.ImageConfig(aspect_ratio='1:1', image_size=image_size),
            ),
        )
        return extract_image(response)


def review(brief, image_bytes):
    instructions = f'''Act as a critical foundation-design teaching assistant.
Assess the ACTUAL IMAGE against ONLY this assignment:\n{brief}\n
Separate compliance with mandatory requirements from subjective artistic quality.
For each issue describe visible evidence and its location; do not invent defects.
A score is indicative, NOT a teacher's grade. Digital pixels cannot establish physical paper size.
Return JSON with exact keys:
compliance (array of objects with requirement, status [met, partial, unclear, unmet], evidence),
strengths (array of strings), issues (array of objects with criterion, observation, location,
impact, suggested_fix), indicative_score (integer 0-100), score_explanation (string),
uncertainty (string), priorities (array of strings).
Reply in Turkish. Strict JSON only.'''
    with client() as gemini_client:
        response = gemini_client.models.generate_content(
            model=TEXT_MODEL,
            contents=types.Content(role='user', parts=[types.Part.from_text(text=instructions), image_part(image_bytes)]),
            config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0),
        )
        return parse_json(response.text)


def revise(brief, original, review_data=None, user_goal='', model=None, image_size='2K', mode='technical'):
    review_data = review_data or {}
    issues = json.dumps(review_data.get('issues', []), ensure_ascii=False)
    priorities = json.dumps(review_data.get('priorities', []), ensure_ascii=False)
    if mode in ('artistic', 'reconstruction', 'Artistic Reconstruction'):
        approach = ('ARTISTIC RECONSTRUCTION: Reimagine the compositional architecture while retaining only '
                    'the strongest design concept from the source. You may substantially reorganize major forms, '
                    'visual hierarchy and negative spaces. Do not retain crowded or ineffective patterns merely '
                    'to resemble the original. Build a distinctive, cohesive composition.')
    else:
        approach = ('TECHNICAL REFINEMENT: Preserve overall spatial layout and artistic identity. Improve '
                    'line clarity, crossings, texture distribution and local geometric-organic transitions only.')
    prompt = f'''Edit the PROVIDED image as a reference for an original improved result.
{approach}

TEACHER ASSIGNMENT (mandatory):\n{brief}

OBSERVED ISSUES:\n{issues}

PRIORITIES:\n{priorities}

STUDENT'S REVISION DIRECTION:\n{user_goal}

Respect the teacher brief above all other instructions. Preserve a two-dimensional design
where required. Do not add labels or text. Output only the revised artwork.'''
    return generate(prompt, reference=original, model=model, image_size=image_size)
