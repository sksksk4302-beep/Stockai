# Stock AI Bot (Data Collector)

This project collects stock data (OHLCV, Investor Trading Value, Shorting Balance) and summary fundamentals (PER, PBR, 52-week High/Low) for a specific ticker using `pykrx`.

It is designed to run on **Google Cloud Functions** and upload the data to **Google Cloud Storage (GCS)**.

## Project Structure

-   `main.py`: Main script (Cloud Function entry point: `cloud_function_entry`).
-   `requirements.txt`: Python dependencies.
-   `.github/workflows/deploy.yml`: GitHub Action for automatic deployment (optional).

## Local Usage

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the script:
    ```bash
    python main.py
    ```
3.  Enter a ticker code (e.g., `005930`).

## GCP Deployment

### Manual Deployment (Console)

1.  Create a Cloud Function (2nd Gen).
2.  Upload this code or connect GitHub.
3.  Set Entry Point to `cloud_function_entry`.
4.  Set Environment Variable `BUCKET_NAME` to your GCS bucket name.

### GitHub Actions Deployment

1.  Enable **Cloud Functions API**, **Cloud Build API**, **Artifact Registry API** in GCP.
2.  Create a Service Account with `Cloud Functions Developer` and `Service Account User` roles.
3.  Download the JSON key and add it to GitHub Secrets as `GCP_SA_KEY`.
4.  Push to `main` branch.
