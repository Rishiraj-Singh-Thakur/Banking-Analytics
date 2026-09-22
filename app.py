from flask import Flask, render_template, request, redirect, url_for, flash
import joblib
import pandas as pd

app = Flask(__name__)

app.secret_key = "banking-analytics-secret-key"


# ============================================================
# LOAD MODELS
# ============================================================

# Loan Approval
loan_model = joblib.load(
    "Models/loan_approval_model.pkl"
)

loan_preprocessor = joblib.load(
    "Models/loan_approval_preprocessor.pkl"
)


# Transaction Anomaly
anomaly_model = joblib.load(
    "Models/transaction_anomaly_model.pkl"
)

anomaly_scaler = joblib.load(
    "Models/transaction_anomaly_scaler.pkl"
)


# Customer Segmentation
segmentation_model = joblib.load(
    "Models/customer_segmentation_model.pkl"
)

segmentation_scaler = joblib.load(
    "Models/customer_segmentation_scaler.pkl"
)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# LOAN APPROVAL
# ============================================================

@app.route("/loan-approval", methods=["GET", "POST"])
def loan_approval():

    if request.method == "POST":

        loan_amount = float(request.form["loan_amount"])
        interest_rate = float(request.form["interest_rate"])
        tenure_months = int(request.form["tenure_months"])

        monthly_rate = interest_rate / (12 * 100)

        emi = (
            loan_amount
            * monthly_rate
            * (1 + monthly_rate) ** tenure_months
        ) / (
            (1 + monthly_rate) ** tenure_months - 1
        )

        new_customer = pd.DataFrame([{
            "gender": request.form["gender"],
            "age": int(request.form["age"]),
            "marital_status": request.form["marital_status"],
            "occupation": request.form["occupation"],
            "annual_income": float(request.form["annual_income"]),
            "cibil_score": float(request.form["cibil_score"]),
            "account_type": request.form["account_type"],
            "account_balance": float(request.form["account_balance"]),
            "loan_type": request.form["loan_type"],
            "loan_amount": loan_amount,
            "interest_rate": interest_rate,
            "tenure_months": tenure_months,
            "emi": emi
        }])

        new_customer_processed = loan_preprocessor.transform(
            new_customer
        )

        prediction = loan_model.predict(
            new_customer_processed
        )[0]

        result = (
            "Loan Approved"
            if prediction == 1
            else "Loan Rejected"
        )

        explanation = (
            f"The trained Decision Tree classified this application "
            f"as {result}. In the overall model analysis, CIBIL Score, "
            "Annual Income and Loan Amount had the highest feature "
            "importance. These values describe how the model used "
            "features for its decisions and should not be interpreted "
            "as causal factors."
        )

        flash(result, "prediction")
        flash(explanation, "explanation")

        # return redirect(url_for("loan_approval"))
        return render_template(
            "loan_approval.html",
            form_data=request.form
        )

    return render_template("loan_approval.html")


# ============================================================
# TRANSACTION ANOMALY DETECTION
# ============================================================

@app.route("/transaction-anomaly", methods=["GET", "POST"])
def transaction_anomaly():

    if request.method == "POST":

        amount = float(request.form["amount"])
        balance = float(
            request.form["balance_after_transaction"]
        )
        transaction_mode = request.form["transaction_mode"]

        new_transaction = pd.DataFrame([{
            "amount": amount,
            "balance_after_transaction": balance,
            "transaction_mode": transaction_mode
        }])

        new_transaction = pd.get_dummies(
            new_transaction,
            columns=["transaction_mode"],
            dtype=int
        )

        # Match training columns
        training_columns = [
            "amount",
            "balance_after_transaction",
            "transaction_mode_ATM",
            "transaction_mode_Cash Deposit",
            "transaction_mode_Credit Card",
            "transaction_mode_Debit Card",
            "transaction_mode_IMPS",
            "transaction_mode_NEFT",
            "transaction_mode_UPI"
        ]

        new_transaction = new_transaction.reindex(
            columns=training_columns,
            fill_value=0
        )

        new_transaction_scaled = anomaly_scaler.transform(
            new_transaction
        )

        prediction = anomaly_model.predict(
            new_transaction_scaled
        )[0]

        if prediction == 1:
            result = "Normal Transaction"

            explanation = (
                "The Isolation Forest classified this transaction "
                "as normal based on the transaction characteristics "
                "provided. The model compares the transaction with "
                "patterns learned from the historical transaction data."
            )

        else:
            result = "Potentially Suspicious"

            explanation = (
                "The Isolation Forest identified this transaction "
                "as potentially unusual compared with the patterns "
                "learned from the historical transaction data. "
                "An anomaly does not necessarily mean confirmed fraud "
                "and should be investigated further."
            )

        flash(result, "prediction")
        flash(explanation, "explanation")

        # return redirect(url_for("transaction_anomaly"))
        return render_template(
            "transaction_anomaly.html",
            form_data=request.form
        )

    return render_template("transaction_anomaly.html")


# ============================================================
# CUSTOMER SEGMENTATION
# ============================================================

@app.route("/customer-segmentation", methods=["GET", "POST"])
def customer_segmentation():

    if request.method == "POST":

        new_customer = pd.DataFrame([{
            "age": float(request.form["age"]),
            "annual_income": float(
                request.form["annual_income"]
            ),
            "cibil_score": float(
                request.form["cibil_score"]
            ),
            "account_balance": float(
                request.form["account_balance"]
            ),
            "total_transactions": float(
                request.form["total_transactions"]
            ),
            "total_transaction_amount": float(
                request.form["total_transaction_amount"]
            ),
            "average_transaction_amount": (
                float(request.form["total_transaction_amount"])
                / float(request.form["total_transactions"])
            )
        }])

        new_customer_scaled = segmentation_scaler.transform(
            new_customer
        )

        cluster = segmentation_model.predict(
            new_customer_scaled
        )[0]

        segment_names = {
            0: "Low Activity Customers",
            1: "Active Customers",
            2: "High Balance Customers",
            3: "High Income Customers"
        }

        result = segment_names[cluster]

        explanation = (
            f"The K-Means model assigned this customer to the "
            f"'{result}' segment. The segmentation was created using "
            "customer demographics, financial information and "
            "transaction behavior. Customers in the same cluster "
            "have relatively similar patterns across these features."
        )

        flash(result, "prediction")
        flash(explanation, "explanation")

        return render_template(
            "customer_segmentation.html",
            form_data=request.form
        )
    return render_template("customer_segmentation.html")


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)