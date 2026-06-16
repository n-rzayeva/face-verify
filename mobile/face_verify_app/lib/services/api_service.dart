import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../config.dart';
import '../models/verification_models.dart';

class ApiService {
  static const _baseUrl = Config.backendBaseUrl;

  static Future<StartResponse> startVerification(String userId) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/verification/start'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'userId': userId}),
    ).timeout(const Duration(seconds: 30));

    if (response.statusCode != 200) {
      throw Exception('Failed to start verification: ${response.body}');
    }

    return StartResponse.fromJson(jsonDecode(response.body));
  }

  static Future<ChallengeResponse> submitChallenge(
    String token,
    List<File> frames,
  ) async {
    final encodedFrames = await Future.wait(
      frames.map((f) async {
        final bytes = await f.readAsBytes();
        return {
          'base64': base64Encode(bytes),
          'label': 'frame',
        };
      }),
    );

    final response = await http.post(
      Uri.parse('$_baseUrl/api/verification/challenge'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'token': token,
        'frames': encodedFrames,
      }),
    ).timeout(const Duration(seconds: 60));

    if (response.statusCode != 200) {
      throw Exception('Challenge failed: ${response.body}');
    }

    return ChallengeResponse.fromJson(jsonDecode(response.body));
  }

  static Future<CompleteResponse> complete(String token) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/verification/complete'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'token': token}),
    ).timeout(const Duration(seconds: 60));

    if (response.statusCode != 200) {
      throw Exception('Complete failed: ${response.body}');
    }

    return CompleteResponse.fromJson(jsonDecode(response.body));
  }
}