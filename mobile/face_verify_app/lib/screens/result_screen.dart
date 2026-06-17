import 'package:flutter/material.dart';
import '../models/verification_models.dart';
import 'start_screen.dart';

class ResultScreen extends StatelessWidget {
  final CompleteResponse response;

  const ResultScreen({super.key, required this.response});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Result')),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              response.passed ? Icons.check_circle : Icons.cancel,
              size: 100,
              color: response.passed ? Colors.green : Colors.red,
            ),
            const SizedBox(height: 24),
            Text(
              response.passed ? 'Verification Passed' : 'Verification Failed',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: response.passed ? Colors.green : Colors.red,
              ),
            ),
            const SizedBox(height: 32),
            _ScoreRow(
              label: 'Similarity Score',
              value: response.similarityScore,
            ),
            const SizedBox(height: 12),
            _ScoreRow(
              label: 'Liveness Score',
              value: response.livenessScore,
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Liveness Label', style: TextStyle(fontSize: 16)),
                Text(
                  response.livenessLabel,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            if (response.failReason != null) ...[
              const SizedBox(height: 24),
              Text(
                'Reason: ${response.failReason}',
                style: const TextStyle(color: Colors.red),
              ),
            ],
            const SizedBox(height: 48),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pushAndRemoveUntil(
                  context,
                  MaterialPageRoute(builder: (_) => const StartScreen()),
                  (_) => false,
                ),
                child: const Text('Try Again'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ScoreRow extends StatelessWidget {
  final String label;
  final double value;

  const _ScoreRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 16)),
        Text(
          value.toStringAsFixed(3),
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}