# PQuick

**Post-Quantum Cryptography Transition Assessment Tool**

## Overview

PQuick is a web-based assessment tool designed to help Italian organizations evaluate their readiness for the post-quantum cryptography transition. The tool provides a structured questionnaire-based approach to identify gaps, measure maturity across different phases, and generate actionable recommendations for transitioning to quantum-safe cryptography.

## Features

- **Phase-Based Assessment**: Organized questionnaire covering multiple phases of post-quantum transition
- **Control Framework**: Comprehensive set of security controls with ownership, horizon, and reference information
- **Scoring System**: Weighted scoring mechanism (Yes=2, Partial=1, No/NA=0) with percentage-based results
- **Smart Recommendations**: Context-aware recommendations tied to each control and answer
- **Multiple Export Formats**:
  - **CSV**: Controls summary for easy data manipulation
  - **JSON**: Simple response data or full detailed export with scores and recommendations
  - **PDF**: Professional report with overall score, phase-by-phase breakdown, priority recommendations, and control appendix
- **Interactive Dashboard**: 
  - Overview with total and phase-level scoring
  - Priority recommendations (critical issues first)
  - Complete controls summary
  - One-click exports
- **Session State Persistence**: Answers are preserved during your assessment session
- **Responsive UI**: Modern web interface with custom styling and intuitive navigation

## Getting Started

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/liviotti/Pquick.git
cd Pquick
streamlit run tool.py
