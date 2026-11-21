"""Generate the test PDFs in tests/pdfs/. Run:  python tests/make_test_pdfs.py

Each document deliberately mixes a known category of claims so we can see whether
the app labels them correctly. Expected verdicts are listed in tests/EXPECTED_RESULTS.md.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).parent / "pdfs"
styles = getSampleStyleSheet()

DOCS = {
    "1_accurate_facts.pdf": ("Company & Science Fact Sheet", [[
        "The Eiffel Tower was completed in 1889 for the Exposition Universelle in Paris.",
        "Apple was founded in 1976 by Steve Jobs, Steve Wozniak and Ronald Wayne.",
        "In 2020, China and Nepal jointly announced that Mount Everest is 8,848.86 metres tall.",
        "The Python programming language was first released by Guido van Rossum in 1991.",
        "The average distance between the Earth and the Moon is about 384,400 kilometres.",
    ]]),
    "2_outdated_stats.pdf": ("2026 Digital Trends Report", [[
        "The world's population currently stands at 7 billion people.",
        "ChatGPT currently has 100 million weekly active users.",
        "The tallest building in the world today is Taipei 101 in Taiwan.",
        "India's population is 1.21 billion, making it the second most populous country in the world.",
    ], [
        "Netflix now has 200 million paid subscribers worldwide.",
        "The current world record for the men's marathon is 2:03:59, set by Haile Gebrselassie.",
    ]]),
    "3_fabricated_claims.pdf": ("Innovation Insights Brief", [[
        "Zentrava Labs, founded in Oslo in 2017, became the first company to reach a $9 trillion "
        "market valuation in 2024.",
        "A 2023 Stanford University study found that 97% of consumers trust AI chatbots more than doctors.",
        "Albert Einstein won the Nobel Prize in Physics in 1935 for his theory of relativity.",
        "The adult human body has 412 bones.",
        "Water boils at 150 degrees Celsius at sea level.",
    ]]),
    "4_trap_mixed.pdf": ("Why Your Brand Needs AI Search: Market Brief", [[
        "AI search is reshaping how customers discover products. Apple, founded in 1976, and Amazon, "
        "founded by Jeff Bezos in 1994, were early winners of the previous search era.",
        "Today, ChatGPT has 100 million weekly active users, and the world's population currently "
        "stands at 7 billion, so the addressable audience is enormous.",
        "According to a 2024 Harvard study, 92% of shoppers now buy only products recommended by AI.",
    ], [
        "The Eiffel Tower, completed in 1925, remains the most visited paid monument in the world.",
        "Our client Nexora Retail grew revenue by 870% in 2023 after adopting GEO.",
        "The Python programming language, first released in 1991, powers most AI tooling.",
    ]]),
}


def build(name, title, pages):
    doc = SimpleDocTemplate(str(OUT / name), pagesize=A4, title=title)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for i, paragraphs in enumerate(pages):
        if i:
            story.append(PageBreak())
        for text in paragraphs:
            story += [Paragraph(text, styles["BodyText"]), Spacer(1, 10)]
    doc.build(story)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, (title, pages) in DOCS.items():
        build(name, title, pages)
        print("wrote", OUT / name)
