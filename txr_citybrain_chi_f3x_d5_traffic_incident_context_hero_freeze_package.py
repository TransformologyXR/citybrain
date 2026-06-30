from txr_citybrain_d5_batch_d1_hero_freeze_packages import run_single_d5

if __name__ == "__main__":
    result = run_single_d5("CHI-F3X-D5")
    print(result["status"])
    raise SystemExit(0 if result["status"].startswith("PASS") else 1)
