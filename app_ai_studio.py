"""Basic Design AI — image-first studio. The SVG editor stays separate."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from services.studio_ai import analyze, create_prompt, generate, review, png_bytes, propose_concepts

st.set_page_config(page_title="Basic Design AI · Image-first Studio", layout="wide")
st.title("Basic Design AI · Image-first Studio")
st.caption("Understand the assignment → Generate with references → Academic critique → Targeted revision")
st.info("Analyze, Generate, Review and Revise make API calls and may incur charges. Saving and downloading are local.")

DEFAULTS = {
    "analysis": None,
    "composition_concepts": None,
    "concept_source_hash": None,
    "selected_concept_index": 0,
    "last_brief": None,
    "generated_image": None,
    "uploaded_image": None,
    "uploaded_file_id": None,
    "active_source": None,  # "generated" or "uploaded"
    "review": None,
    "review_hash": None,
    "revised": None,
    "revision_mode_used": None,
    "revision_source_hash": None,
    "generation_prompt": None,
    "generation_settings": None,
    "generation_reference_hash": None,
    "generation_input_hash": None,
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def current_image():
    source = st.session_state.active_source
    if source == "generated":
        return st.session_state.generated_image
    if source == "uploaded":
        return st.session_state.uploaded_image
    return None


def clear_assessment():
    st.session_state.review = None
    st.session_state.review_hash = None
    st.session_state.revised = None
    st.session_state.revision_mode_used = None
    st.session_state.revision_source_hash = None


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


brief = st.text_area(
    "1. Teacher assignment — only the original instructions",
    height=170, key="brief_input", placeholder="Paste the teacher's actual assignment here"
)
if st.button("Analyze assignment (API)", disabled=not bool(brief.strip())):
    try:
        with st.spinner("Analyzing requirements..."):
            st.session_state.analysis = analyze(brief)
        st.session_state.last_brief = brief
        clear_assessment()
        st.success("Assignment analyzed.")
    except Exception as error:
        st.error(f"Analysis failed: {error}")
        st.exception(error)

if st.session_state.analysis:
    st.subheader("Extracted requirements — verify before generating")
    for title, field in [
        ("Mandatory", "mandatory"), ("Forbidden", "forbidden"),
        ("Uncertain", "uncertain"), ("Design principles", "design_principles"),
        ("Artistic freedom", "artistic_freedom")
    ]:
        with st.expander(title, expanded=title == "Mandatory"):
            for item in st.session_state.analysis.get(field, []):
                st.write("•", item)
    st.caption("Compare the analysis with the teacher's original brief. The original brief remains authoritative.")

st.divider()
st.header("2. High-quality image generation")
model_label = st.selectbox(
    "Image model",
    ["Gemini 3.1 Flash Image — lower cost", "Gemini 3 Pro Image — quality test"], index=1
)
selected_model = "gemini-3-pro-image" if "Pro Image" in model_label else "gemini-3.1-flash-image"
image_size = st.selectbox("Output resolution", ["1K", "2K", "4K"], index=1)
st.caption("One image per Generate click. Check current API billing; input and output may incur charges.")
direction = st.text_area("Additional artistic direction — not teacher requirements", height=100, key="art_direction")
st.caption("Teacher brief and artistic preferences must remain separate.")
reference = st.file_uploader(
    "Optional visual style reference (PNG/JPG, images you have rights to use)",
    type=["png", "jpg", "jpeg"], key="reference_upload"
)
if reference is not None:
    st.image(reference, width=260, caption="Style reference — not for copying")

# Optional concept planning inside the existing Studio; never triggers image generation.
st.subheader("Composition Concept Lab · optional")
st.caption("Plan three original composition ideas before spending on image generation. "
           "The concept button calls the text API and may incur a smaller charge; selecting a concept is free.")
concept_basis = hashlib.sha256((brief + direction + json.dumps(st.session_state.analysis or {},
                                     ensure_ascii=False, sort_keys=True)).encode("utf-8")).hexdigest()
analysis_ready = bool(st.session_state.analysis and brief.strip() and st.session_state.last_brief == brief)
if st.button("Propose 3 composition concepts (text API)", disabled=not analysis_ready):
    try:
        with st.spinner("Developing three alternative composition strategies..."):
            plans = propose_concepts(brief, st.session_state.analysis, direction)
        st.session_state.composition_concepts = plans
        st.session_state.concept_source_hash = concept_basis
        st.session_state.selected_concept_index = 0
        st.success("Three composition plans ready. No image was generated.")
    except Exception as error:
        st.error(f"Concept planning failed: {error}")
        st.exception(error)

concept_instruction = ""
valid_plans = (st.session_state.composition_concepts is not None
               and st.session_state.concept_source_hash == concept_basis and analysis_ready)
if st.session_state.composition_concepts and not valid_plans:
    st.warning("The assignment, analysis, or art direction changed. Previously planned concepts are stale; generate new concepts before using them.")
if valid_plans:
    plans = st.session_state.composition_concepts
    titles = [f"{idx + 1}. {plan['title']}" for idx, plan in enumerate(plans)]
    selection = st.radio("Choose one concept for the next image", range(3),
                         format_func=lambda idx: titles[idx], horizontal=False,
                         key="selected_concept_index")
    for idx, plan in enumerate(plans):
        with st.expander(titles[idx], expanded=(idx == selection)):
            for name, field in [
                ("Core idea", "idea"), ("Spatial organization", "layout"),
                ("Focal transformation", "focal_transformation"),
                ("Designed negative space", "negative_space"),
                ("Texture plan", "texture_strategy"),
                ("Why it is different", "originality_rationale"),
                ("Risks", "risks")
            ]:
                st.markdown(f"**{name}:** {plan[field]}")
    use_selected_concept = st.checkbox("Include selected concept in next image prompt", value=True)
    if use_selected_concept:
        concept_instruction = ("\n\nSELECTED COMPOSITION CONCEPT — OPTIONAL ART DIRECTION:\n"
                               + plans[selection]["visual_prompt"]
                               + "\nThis concept may not override the teacher assignment.")

if st.session_state.analysis and brief.strip():
    if st.session_state.last_brief != brief:
        st.warning("The assignment text changed. Analyze it again before generating.")
    else:
        default_prompt = create_prompt(brief, st.session_state.analysis, direction + concept_instruction)
        # A stable key permits manual edits; update only when the input to the prompt builder changes.
        prompt_inputs = hashlib.sha256((brief + json.dumps(st.session_state.analysis, sort_keys=True, ensure_ascii=False) + direction + concept_instruction).encode("utf-8")).hexdigest()
        if st.session_state.get("prompt_inputs_hash") != prompt_inputs:
            st.session_state["editable_prompt"] = default_prompt
            st.session_state["prompt_inputs_hash"] = prompt_inputs
        prompt = st.text_area("Inspect or edit generation prompt", key="editable_prompt", height=290)
        st.warning(f"Paid generation: 1 image · {selected_model} · {image_size}. Confirm reference and prompt before clicking.")
        if st.button("Generate ONE image (API)"):
            try:
                reference_data = reference.getvalue() if reference is not None else None
                with st.spinner("Generating one image..."):
                    data = generate(prompt, reference=reference_data, model=selected_model, image_size=image_size)
                # Crucially, generated imagery is independent of the upload widget.
                st.session_state.generated_image = data
                st.session_state.active_source = "generated"
                st.session_state.generation_prompt = prompt
                st.session_state.generation_settings = {"model": selected_model, "resolution": image_size}
                st.session_state.generation_reference_hash = sha256_bytes(reference_data) if reference_data else None
                st.session_state.generation_input_hash = hashlib.sha256((prompt + selected_model + image_size).encode()).hexdigest()
                clear_assessment()
                st.success("New image returned by Gemini and selected as active design.")
            except Exception as error:
                st.error(f"Generation failed: {error}")
                st.exception(error)

st.caption("Upload an existing drawing only when you want to assess that drawing instead of the generated result.")
existing = st.file_uploader("Existing design PNG/JPG", type=["png", "jpg", "jpeg"], key="existing_upload")
if existing is not None:
    file_bytes = existing.getvalue()
    file_id = (existing.name, len(file_bytes), sha256_bytes(file_bytes))
    if file_id != st.session_state.uploaded_file_id:
        st.session_state.uploaded_image = png_bytes(file_bytes)
        st.session_state.uploaded_file_id = file_id
        # Do NOT automatically overwrite the active generated image.
        st.info("Existing drawing loaded separately. Select it below if you want to review it.")

available_sources = []
if st.session_state.generated_image is not None:
    available_sources.append("generated")
if st.session_state.uploaded_image is not None:
    available_sources.append("uploaded")
if available_sources:
    labels = {"generated": "Gemini-generated image", "uploaded": "Uploaded existing design"}
    if st.session_state.active_source not in available_sources:
        st.session_state.active_source = available_sources[0]
    chosen_source = st.radio(
        "Which image should be displayed and reviewed?",
        available_sources,
        index=available_sources.index(st.session_state.active_source),
        format_func=lambda x: labels[x], horizontal=True,
    )
    if chosen_source != st.session_state.active_source:
        st.session_state.active_source = chosen_source
        clear_assessment()

    if st.session_state.active_source == "generated" and st.session_state.generation_settings:
        st.caption("Active image: Gemini-generated · " + str(st.session_state.generation_settings))
    elif st.session_state.active_source == "uploaded":
        st.caption("Active image: uploaded existing drawing (not a newly generated image)")

    active_data = current_image()
    image_digest = sha256_bytes(active_data)
    st.image(active_data, width=650, caption="Current selected design")
    st.download_button("Download selected PNG", active_data, file_name="selected_design.png", mime="image/png")

    if st.session_state.generated_image is not None and st.session_state.uploaded_image is not None:
        with st.expander("Compare generated image and uploaded reference", expanded=False):
            a, b = st.columns(2)
            with a:
                st.image(st.session_state.generated_image, caption="Gemini-generated", use_container_width=True)
            with b:
                st.image(st.session_state.uploaded_image, caption="Uploaded existing design", use_container_width=True)

    st.divider()
    st.header("3. Academic Design Review")
    if st.button("Review selected design (API)", disabled=not bool(brief.strip())):
        try:
            with st.spinner("Reviewing against teacher brief..."):
                result = review(brief, active_data)
            st.session_state.review = result
            st.session_state.review_hash = sha256_bytes((brief + image_digest).encode("utf-8"))
            st.session_state.revised = None
            st.session_state.revision_source_hash = None
        except Exception as error:
            st.error(f"Review failed: {error}")
            st.exception(error)

    review_current = st.session_state.review_hash == sha256_bytes((brief + image_digest).encode("utf-8"))
    if st.session_state.review:
        if not review_current:
            st.warning("The image or teacher brief changed. Review again to assess the selected image.")
        else:
            result = st.session_state.review
            st.metric("Indicative AI assessment — NOT a teacher grade", f"{result.get('indicative_score', '?')}/100")
            st.write("**Score rationale:**", result.get("score_explanation", ""))
            st.write("**Uncertainty:**", result.get("uncertainty", ""))
            with st.expander("Requirement compliance", expanded=True):
                for row in result.get("compliance", []):
                    st.write(f"**{row.get('requirement', '')} — {row.get('status', '')}**: {row.get('evidence', '')}")
            with st.expander("Strengths"):
                for item in result.get("strengths", []):
                    st.write("•", item)
            with st.expander("All observed issues", expanded=True):
                for issue in result.get("issues", []):
                    st.write(f"**{issue.get('criterion', '')}** — {issue.get('observation', '')} (Location: {issue.get('location', 'unknown')})")
                    st.write("Impact:", issue.get("impact", ""))
                    st.write("Suggestion:", issue.get("suggested_fix", ""))


    st.divider()
    st.header("4. Artistic Revision Studio")
    st.caption("Choose whether to polish the current design or rethink its composition. Each revision generates one potentially paid image.")
    revision_mode = st.radio(
        "Revision approach",
        ["Artistic Reconstruction", "Technical Refinement"],
        horizontal=True,
        help="Reconstruction permits substantial composition changes; Refinement keeps the existing layout.",
    )
    if revision_mode == "Artistic Reconstruction":
        st.info("Rethink spatial organization while retaining the central design idea. Expect meaningful composition changes, not pixel-accurate editing.")
        default_goal = (
            "Keep the idea of rigid square-based geometry evolving into organic flow. "
            "Rebuild the layout with ONE powerful focal transformation, clear supporting relationships, "
            "more intentional white space, and dramatically better readability. "
            "Do not repeat a pile of nested squares or excessive parallel ribbons. "
            "Use varied scale, controlled ink density, and an original asymmetric silhouette."
        )
    else:
        st.info("Keep the layout, focal point and main forms. Improve line discipline, intersections and purposeful texture.")
        default_goal = (
            "Preserve the existing overall arrangement and recognizable geometry. "
            "Clean up muddy intersections, remove redundant contours, maintain crisp boundaries, "
            "clarify primary and secondary line weights, and refine selective hatching. "
            "Do not introduce extra decorative motifs."
        )

    custom_goal = st.text_area(
        "Artistic director notes (optional)", value=default_goal,
        height=140, key=f"revision_goal_{revision_mode}",
    )
    review_issues = []
    if review_current and st.session_state.review:
        review_issues = st.session_state.review.get("issues", [])
    else:
        st.caption("No current Academic Review: you may still reconstruct the artwork. Review is optional for artistic revisions.")

    if revision_mode == "Artistic Reconstruction":
        revision_prompt = f"""ARTISTIC RECONSTRUCTION — a substantial redesign based on the attached artwork.

TEACHER ASSIGNMENT — binding requirements:
{brief}

STUDENT'S CURRENT ARTWORK: attached image. Study its core idea, not its literal coordinates.

THE ARTISTIC PROBLEM:
The existing drawing has potential but lacks a truly memorable integrated composition.
It may show overloaded geometric clusters, parallel contours used as decoration,
and weakly connected areas. Correct these issues by RECOMPOSING rather than merely retouching.

ART DIRECTOR'S DESIGN STRATEGY:
1. Select a single compelling square-to-organic transformation as the visual thesis.
2. Reorganize the primary shapes and negative-space pathways around that thesis.
3. Create one decisive focal relationship with subordinate shapes, not equal-sized icons.
4. Make organic contours structurally originate from and change geometric boundaries.
5. Replace clutter with meaningful contrasts of black masses, fine texture and open white.
6. Where required by the teacher, employ distinct line textures purposefully.
7. Make the overall visual silhouette visually memorable even at thumbnail size.
8. Do not draw a decorative border, text, photographic effects or 3-D forms.

STUDENT'S ADDITIONAL DIRECTION:
{custom_goal}

ACADEMIC OBSERVATIONS (advisory, do not blindly copy):
{json.dumps(review_issues, ensure_ascii=False)}

You have permission to substantially change positions, sizes, rhythm and connections.
Do not simply return a near-duplicate or retouch a few lines.
Keep the original conceptual seed, but create a newly composed and superior original artwork.
The teacher assignment overrides any incompatible preference.
Return exactly ONE finished black-and-white square artwork, no annotations."""
    else:
        revision_prompt = f"""TECHNICAL REFINEMENT — edit the attached artwork conservatively.

TEACHER ASSIGNMENT — binding requirements:
{brief}

Keep the present composition, major contours, visual hierarchy, scale, and focal point.
Do not relocate or replace the principal geometric-organic structures.
Enhance line precision, geometric junctions, readability, intentional hatching,
black-fill boundaries, and quiet negative space. Avoid adding unnecessary complexity.

STUDENT'S ADDITIONAL DIRECTION:
{custom_goal}

ACADEMIC OBSERVATIONS (advisory):
{json.dumps(review_issues, ensure_ascii=False)}

This is a restrained craft improvement, not an artistic redesign.
Maintain the teacher's conditions. Return exactly ONE finished artwork, no labels."""

    with st.expander("Preview exact revision prompt — free", expanded=False):
        st.code(revision_prompt, language="text")
    st.warning(f"Paid revision: 1 image · {selected_model} · {image_size}. Original will be supplied as image input.")
    if st.button("Generate revised version (API)"):
        if not brief.strip():
            st.error("Enter the teacher assignment first.")
        else:
            try:
                with st.spinner(f"Generating {revision_mode.lower()}..."):
                    revised_data = generate(
                        revision_prompt, reference=active_data,
                        model=selected_model, image_size=image_size,
                    )
                st.session_state.revised = revised_data
                st.session_state.revision_mode_used = revision_mode
                st.session_state.revision_source_hash = image_digest
                st.success("Revised image received. Compare the original and revised drawings below.")
            except Exception as error:
                st.error(f"Revision failed: {error}")
                st.exception(error)

    if st.session_state.revised is not None and st.session_state.revision_source_hash == image_digest:
        st.header("5. Before / After")
        st.caption("Revision mode: " + str(st.session_state.revision_mode_used))
        original_col, revised_col = st.columns(2)
        with original_col:
            st.image(active_data, caption="Original", use_container_width=True)
        with revised_col:
            st.image(st.session_state.revised, caption="Revised", use_container_width=True)
        st.download_button("Download revised PNG", st.session_state.revised, file_name="revised_design.png", mime="image/png")
        st.caption("Assess whether the composition improved; a newly generated revision may still require judgment.")

st.divider()
st.header("6. Save project locally — no API charge")
if st.button("Save current project"):
    folder = Path("projects") / ("image_studio_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "assignment.txt").write_text(brief, encoding="utf-8")
    for key in ("analysis", "review", "composition_concepts"):
        if st.session_state.get(key):
            (folder / f"{key}.json").write_text(json.dumps(st.session_state[key], ensure_ascii=False, indent=2), encoding="utf-8")
    if st.session_state.generated_image is not None:
        (folder / "generated.png").write_bytes(st.session_state.generated_image)
    if st.session_state.uploaded_image is not None:
        (folder / "uploaded.png").write_bytes(st.session_state.uploaded_image)
    if st.session_state.revised is not None:
        (folder / "revised.png").write_bytes(st.session_state.revised)
    (folder / "metadata.json").write_text(json.dumps({
        "active_source": st.session_state.active_source,
        "generation_settings": st.session_state.generation_settings,
        "generation_reference_hash": st.session_state.generation_reference_hash,
        "generation_input_hash": st.session_state.generation_input_hash,
        "revision_mode": st.session_state.revision_mode_used,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    st.success(f"Saved to {folder}")
