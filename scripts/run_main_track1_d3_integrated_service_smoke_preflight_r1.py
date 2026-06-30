from track1_d3_completion_lib import run_integrated_preflight


if __name__ == "__main__":
    decision = run_integrated_preflight()
    print(f"MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE-PREFLIGHT-R1: {decision['status']}")
