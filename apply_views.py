import os
from bigquery_client import BigQueryClient

def main():
    bq_client = BigQueryClient()
    
    # SQL files to execute
    sql_files = [
        "create_korean_view.sql",
        "create_looker_views.sql"
    ]
    
    print("Starting Looker View creation...")
    
    for sql_file in sql_files:
        file_path = os.path.join(os.getcwd(), sql_file)
        print(f"Applying {sql_file}...")
        
        success = bq_client.create_views_from_file(file_path)
        
        if success:
            print(f"Successfully applied {sql_file}")
        else:
            print(f"Failed to apply {sql_file}")
            
    print("Looker View creation process finished.")

if __name__ == "__main__":
    main()
