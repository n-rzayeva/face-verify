import 'package:flutter/material.dart';
import 'screens/start_screen.dart';

void main() {
  runApp(const FaceVerifyApp());
}

class FaceVerifyApp extends StatelessWidget {
  const FaceVerifyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Face Verification',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const StartScreen(),
    );
  }
}