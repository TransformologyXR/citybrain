from track1_d3_completion_lib import run_integrated_smoke


if __name__ == "__main__":
    decision = run_integrated_smoke()
    print(f"MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE: {decision['status']}")
