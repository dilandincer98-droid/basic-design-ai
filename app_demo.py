"""Basic Design AI — public, API-free portfolio demonstration.

This file intentionally imports no Gemini client, private service module,
or environment configuration. No API calls are possible through this app.
"""
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Basic Design AI | Portfolio Demo",
    page_icon="🎨",
    layout="wide",
)

st.title("Basic Design AI")
st.caption("Image-first design assistant · Public portfolio demonstration")
st.success("Public demo mode — no Gemini API calls, no AI generation, no account charges.")

st.markdown(
    """**Basic Design AI** explores how AI can support foundation-design coursework:
    interpreting assignments, developing composition concepts, producing black-and-white
    compositions, assessing artistic choices, and proposing revisions.

    This public demonstration shows the **workflow and example outputs only**.
    The live AI functions are intentionally unavailable so visitors cannot use
    the project owner's Gemini API account.
    """
)

st.divider()
st.subheader("The design workflow")
steps = [
    ("01 · Understand", "Extract mandatory requirements, constraints and artistic freedom from the teacher's brief."),
    ("02 · Concept", "Compare three distinct composition ideas before generating an image."),
    ("03 · Generate", "Turn the selected concept into an original two-dimensional image."),
    ("04 · Review", "Separate assignment compliance from subjective artistic-quality feedback."),
    ("05 · Revise", "Choose between artistic reconstruction and technical refinement."),
]
for heading, description in steps:
    with st.expander(heading, expanded=heading.startswith("01")):
        st.write(description)

st.divider()
st.subheader("Example artwork")
st.caption(
    "If example images are included in the public repository's assets folder, "
    "they appear below. You can also compare two images temporarily in your browser session."
)

asset_dir = Path(__file__).resolve().parent / "assets"
examples = [asset_dir / "example_original.png", asset_dir / "example_revised.png"]
existing = [p for p in examples if p.is_file()]
if existing:
    columns = st.columns(len(existing))
    for column, path in zip(columns, existing):
        with column:
            label = "Original composition" if "original" in path.name else "Revised composition"
            st.image(str(path), caption=label, use_container_width=True)
else:
    st.info(
        "No public example images have been added yet. "
        "To show portfolio examples, add assets/example_original.png "
        "and optionally assets/example_revised.png to this repository."
    )

with st.expander("Compare your own images locally — no AI", expanded=False):
    st.caption(
        "Optional visual preview only. Uploaded images are not sent to Gemini, "
        "saved to disk, or placed in the public repository. "
        "As with any public website, avoid uploading confidential material."
    )
    col1, col2 = st.columns(2)
    with col1:
        original = st.file_uploader(
            "First image", type=["png", "jpg", "jpeg"], key="public_original"
        )
        if original is not None:
            st.image(original, caption="Image A", use_container_width=True)
    with col2:
        revised = st.file_uploader(
            "Second image", type=["png", "jpg", "jpeg"], key="public_revised"
        )
        if revised is not None:
            st.image(revised, caption="Image B", use_container_width=True)

st.divider()
st.subheader("Technology")
st.write("Python · Streamlit · Google Gemini API (private development only)")
st.info(
    "This public deployment does not read GEMINI_API_KEY or import Gemini services. "
    "Analysis, concept planning, image generation, review and revision are disabled "
    "by design—not merely hidden behind buttons."
)
st.caption("Portfolio demonstration · AI-generated assessments are not official teacher grades.")
