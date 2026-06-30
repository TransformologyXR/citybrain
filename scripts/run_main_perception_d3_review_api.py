from track1_d3_completion_lib import run_review_api


if __name__ == "__main__":
    decision = run_review_api()
    print(f"MAIN-PERCEPTION-D3-REVIEW-API: {decision['status']}")
