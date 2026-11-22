#!/usr/bin/env python3
"""Build current per-model Arabic scope and safety PDFs without training or inference."""
from ner_safety_pdf import build_ner_safety_pdf
from pricing_safety_pdf import build_pricing_safety_pdf
from vision_audit_pdf import build_vision_audit_pdf
from rag_safety_pdf import build_rag_safety_pdf


def main():
    build_ner_safety_pdf()
    build_pricing_safety_pdf()
    build_vision_audit_pdf()
    build_rag_safety_pdf()


if __name__=='__main__':main()
