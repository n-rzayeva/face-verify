class StartResponse {
  final String token;
  final List<String> challenges;

  StartResponse({required this.token, required this.challenges});

  factory StartResponse.fromJson(Map<String, dynamic> json) {
    return StartResponse(
      token: json['token'],
      challenges: List<String>.from(json['challenges']),
    );
  }
}

class ChallengeResponse {
  final bool passed;
  final List<String> failReasons;
  final String? nextChallenge;
  final bool allComplete;
  final String token;

  ChallengeResponse({
    required this.passed,
    this.failReasons = const [],
    this.nextChallenge,
    required this.allComplete,
    required this.token,
  });

  factory ChallengeResponse.fromJson(Map<String, dynamic> json) {
    return ChallengeResponse(
      passed: json['passed'],
      failReasons: List<String>.from(json['fail_reasons'] ?? []),
      nextChallenge: json['next_challenge'],
      allComplete: json['all_complete'],
      token: json['token'],
    );
  }
}

class CompleteResponse {
  final bool passed;
  final double similarityScore;
  final double livenessScore;
  final String livenessLabel;
  final String? failReason;

  CompleteResponse({
    required this.passed,
    required this.similarityScore,
    required this.livenessScore,
    required this.livenessLabel,
    this.failReason,
  });

  factory CompleteResponse.fromJson(Map<String, dynamic> json) {
    return CompleteResponse(
      passed: json['passed'],
      similarityScore: (json['similarity_score'] as num).toDouble(),
      livenessScore: (json['liveness_score'] as num).toDouble(),
      livenessLabel: json['liveness_label'] ?? '',
      failReason: json['fail_reason'],
    );
  }
}