
# 🚀 Spark Delta Architecture – Lakehouse Project

This project demonstrates a modern **Lakehouse architecture** using **Apache Spark** and **Delta Lake**. It showcases how to ingest, transform, and manage large-scale datasets with ACID transactions, schema evolution, and efficient data versioning.

![Lakehouse Architecture](Images/Diagram.jpg)

## 📂 Project Structure

```
spark-delta-architecture/
├── app/                    # Main application logic (data processing, orchestration, etc.)
├── configs/                # Configuration files (e.g. paths, schema definitions, Spark configs)
├── hive-metastore/         # Metastore-related setup for Delta Lake (if applicable)
├── scripts/                # Standalone PySpark scripts for ETL and utilities
├── test/                   # Test data and unit test scripts
├── .dockerignore           # Files/folders to exclude from Docker builds
├── .gitignore              # Files/folders to exclude from Git versioning
├── .make-release-support   # Supporting files for release automation (optional)
├── .release                # Release versioning information (optional)
├── Dockerfile              # Docker setup for running the Spark/Delta app
├── Makefile                # Automation commands for build/test/deploy (if used)
├── README.md               # Project documentation and usage guide
```

## 🎯 Features

- ✅ Lakehouse architecture with Delta Lake
- ✅ ACID-compliant data storage
- ✅ Time travel and version control of data
- ✅ Schema enforcement & evolution
- ✅ Real-time and batch data processing with PySpark

## 🛠️ Technologies Used

- **Apache Spark** (PySpark)
- **Delta Lake**
- **Python 3.x**
- **Jupyter Notebooks / Databricks**
- **Parquet, CSV, JSON (data formats)**

## ⚙️ Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/parbatrajpurohit/spark-delta-architecture.git
   cd spark-delta-architecture
   ```

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run PySpark with Delta support**:
   ```bash
   pyspark --packages io.delta:delta-core_2.12:2.1.0
   ```

   > 💡 *Version may vary depending on your Spark installation.*


## 📊 Use Cases

- Data Warehousing
- Real-Time Analytics
- Data Lake Management
- Historical Data Tracking (Time Travel)

## 🚧 Future Improvements

- Add unit tests with `pytest`
- Integrate logging and exception handling
- Automate pipeline with Apache Airflow
- Deploy with Docker for local testing

## 👨‍💻 Author

**Parbat Singh Rajpurohit**  
[GitHub](https://github.com/parbatrajpurohit) | [LinkedIn](https://www.linkedin.com/in/parbat-10171418a/)

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
