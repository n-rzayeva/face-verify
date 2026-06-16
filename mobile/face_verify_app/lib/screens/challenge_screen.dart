import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';
import '../services/api_service.dart';
import '../models/verification_models.dart';
import 'result_screen.dart';

class ChallengeScreen extends StatefulWidget {
  final String token;
  final List<String> challenges;
  final String userId;

  const ChallengeScreen({
    super.key,
    required this.token,
    required this.challenges,
    required this.userId,
  });

  @override
  State<ChallengeScreen> createState() => _ChallengeScreenState();
}

class _ChallengeScreenState extends State<ChallengeScreen> {
  CameraController? _cameraController;
  int _currentChallengeIndex = 0;
  String get _currentChallenge => widget.challenges[_currentChallengeIndex];
  String _guidance = '';
  bool _capturing = false;
  bool _waiting = false;
  int _countdown = 3;
  String _token = '';

  @override
  void initState() {
    super.initState();
    _token = widget.token;
    _initCamera();
    _updateGuidance();
  }

  void _updateGuidance() {
    setState(() {
      switch (_currentChallenge) {
        case 'BLINK':
          _guidance = 'Please blink naturally when ready';
          break;
        case 'TURN_LEFT':
          _guidance = 'Please turn your head to the RIGHT when ready'; // flipped for front camera
          break;
        case 'TURN_RIGHT':
          _guidance = 'Please turn your head to the LEFT when ready'; // flipped for front camera
          break;
      }
    });
  }

  String _failMessage(List<String> reasons) {
    if (reasons.isEmpty) return 'Not detected clearly, try again.';
    const messages = {
      'BLURRY': 'Please hold your phone steady.',
      'POOR_LIGHTING': 'Please find better lighting.',
      'FACE_NOT_DETECTED': 'No face detected. Look directly at the camera.',
      'FACE_TOO_FAR': 'Please move closer to the camera.',
      'FACE_OBSCURED': 'Your face is partially covered.',
      'ACTION_NOT_DETECTED': 'Action not detected. Please try again.',
    };
    return messages[reasons.first] ?? 'Please try again.';
  }

  Future<void> _initCamera() async {
    await Permission.camera.request();
    final cameras = await availableCameras();
    final front = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.front,
    );

    _cameraController = CameraController(
      front,
      ResolutionPreset.medium,
      enableAudio: false,
    );

    await _cameraController!.initialize();
    if (!mounted) return;
    setState(() {});
  }

  Future<void> _startCapture() async {
    if (_capturing || _waiting) return;
    _waiting = true;

    // Countdown
    for (int i = 3; i >= 1; i--) {
      setState(() {
        _countdown = i;
        _guidance = 'Perform action in $i...';
      });
      await Future.delayed(const Duration(seconds: 1));
    }

    setState(() {
      _guidance = 'Capturing...';
      _capturing = true;
    });

    // Capture 10 frames rapidly
    final List<File> frames = [];
    for (int i = 0; i < 10; i++) {
      try {
        final xFile = await _cameraController!.takePicture();
        frames.add(File(xFile.path));
        await Future.delayed(const Duration(milliseconds: 150));
      } catch (e) {
        debugPrint('Capture error: $e');
      }
    }

    _waiting = false;
    _capturing = false;

    await _submitChallenge(frames);
  }

  Future<void> _submitChallenge(List<File> frames) async {
    setState(() => _guidance = 'Analyzing...');

    try {
      final response = await ApiService.submitChallenge(
        _token,
        frames,
      );

      debugPrint('Response: passed=${response.passed}, failReasons=${response.failReasons}');

      _token = response.token;

      if (!response.passed) {
        if (response.failReasons.contains('MAX_ATTEMPTS_EXCEEDED')) {
          if (!mounted) return;
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (_) => ResultScreen(
                response: CompleteResponse(
                  passed: false,
                  similarityScore: 0,
                  livenessScore: 0,
                  failReason: 'Max attempts exceeded for $_currentChallenge',
                ),
              ),
            ),
          );
          return;
        }

        final message = _failMessage(response.failReasons);
        _updateGuidance();
        setState(() => _guidance = '$_guidance\n$message');
        return;
      }

      if (response.allComplete) {
        final result = await ApiService.complete(_token);
        if (!mounted) return;
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => ResultScreen(response: result)),
        );
        return;
      }

      _currentChallengeIndex++;
      _updateGuidance();
    } catch (e) {
      setState(() => _guidance = 'Error: ${e.toString()}');
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Verification')),
      body: Column(
        children: [
          Expanded(
            flex: 3,
            child: _cameraController?.value.isInitialized == true
                ? CameraPreview(_cameraController!)
                : const Center(child: CircularProgressIndicator()),
          ),
          Expanded(
            flex: 1,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              color: Colors.black87,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Challenge ${_currentChallengeIndex + 1} of ${widget.challenges.length}',
                    style: const TextStyle(color: Colors.white60, fontSize: 14),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _guidance,
                    style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  if (!_capturing && !_waiting)
                    ElevatedButton(
                      onPressed: _startCapture,
                      child: const Text('Ready — Start Capture'),
                    )
                  else
                    const CircularProgressIndicator(color: Colors.white),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}