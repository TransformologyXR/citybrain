from txr_citybrain_d4_batch_d1_remaining_replay_face_proofs import run_single_d4, LANES

if __name__ == "__main__":
    result = run_single_d4("CHI-F3X-D4")
    print(result["status"])
    raise SystemExit(0 if result["status"].startswith("PASS") else 1)
