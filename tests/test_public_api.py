from focuslens import AttentionAnalysis, FaceObservation, analyze_attention
from focuslens.attention import AttentionAnalysis as AttentionAnalysisFromModule


def test_package_exports_detailed_attention_api():
    analysis = analyze_attention(FaceObservation(detected=False))

    assert AttentionAnalysis is AttentionAnalysisFromModule
    assert isinstance(analysis, AttentionAnalysis)
