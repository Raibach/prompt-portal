#!/usr/bin/env python3
"""Call DeepSeek chat API using DEEPSEEK_API_KEY from environment or .env.

Usage:
  python3 scripts/deepseek_call.py --prompt "Your prompt here"

This script prints the JSON response.
"""
import os
import sys
import json
import argparse


def load_key():
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        return key.strip()
    env_path = os.path.join(os.getcwd(), ".env")
    try:
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.strip().split("=", 1)[1]
    except FileNotFoundError:
        pass
    return None


def call_deepseek(payload, key, timeout=30):
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        import requests
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        return r.status_code, r.text
    except Exception:
        try:
            from urllib import request
            data = json.dumps(payload).encode()
            req = request.Request(url, data=data, headers=headers)
            with request.urlopen(req, timeout=timeout) as resp:
                return resp.getcode(), resp.read().decode()
        except Exception as e:
            return None, f"Request failed: {e}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", "-p", default="Write a short helper to reverse a string in Python")
    p.add_argument("--model", "-m", default="DeepSeek-V3.2-Speciale")
    p.add_argument("--stream", action="store_true")
    args = p.parse_args()

    key = load_key()
    if not key:
        print("ERROR: DEEPSEEK_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(2)

    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": args.prompt}
        ],
        "stream": bool(args.stream)
    }

    status, body = call_deepseek(payload, key)
    if status is None:
        print(body, file=sys.stderr)
        sys.exit(3)

    try:
        parsed = json.loads(body)
        print(json.dumps(parsed, indent=2))
    except Exception:
        print(body)


if __name__ == '__main__':
    main()
