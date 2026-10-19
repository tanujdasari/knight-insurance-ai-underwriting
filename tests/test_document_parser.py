# ============================================================
# IMPORTS
# ============================================================

# Import the document parsing functions that we want to test.
#
# parse_csv():
# Reads CSV files and extracts structured records.
#
# parse_txt():
# Decodes plain-text files and extracts their contents.
#
# parse_broker_email():
# Processes pasted broker email as a separate evidence source.
from services.document_parser import (
    parse_csv,
    parse_txt,
    parse_broker_email,
)


# ============================================================
# TEST 1: CSV FILE WITH THREE VEHICLE RECORDS
# ============================================================

def test_csv_three_rows():
    """
    Verify that the CSV parser correctly processes
    a file containing three vehicle records.

    Scenario:
        A CSV file contains one header row and
        three vehicle data rows.

    Expected:
        status = success
        row_count = 3
        evidence sources = 3

    The header row must not be counted as a vehicle.
    """

    # Create sample CSV content as bytes.
    #
    # The prefix b indicates a bytes object.
    # \n represents a newline character.
    #
    # The first line contains the column headers.
    # The next three lines contain vehicle records.
    content = (
        b"vehicle_id,year\n"
        b"V001,2022\n"
        b"V002,2023\n"
        b"V003,2024\n"
    )

    # Pass the simulated CSV file to the parser.
    result = parse_csv("vehicles.csv", content)

    # Verify that the file was parsed successfully.
    assert result["status"] == "success"

    # Verify that exactly three data records were counted.
    assert result["row_count"] == 3

    # Verify that evidence was created for each vehicle row.
    assert len(result["sources"]) == 3


# ============================================================
# TEST 2: CSV FILE WITH INVALID ENCODING
# ============================================================

def test_csv_invalid_encoding():
    """
    Verify that the CSV parser handles invalid UTF-8 data.

    Scenario:
        The uploaded CSV contains bytes that cannot
        be decoded using UTF-8.

    Expected:
        status = failed
        row_count = None

    The parser should return a failure result instead
    of allowing the decoding exception to crash the app.
    """

    # Supply an invalid UTF-8 byte sequence.
    result = parse_csv("vehicles.csv", b"\xff\xfe\xfa")

    # Confirm that parsing failed.
    assert result["status"] == "failed"

    # Confirm that no usable vehicle count is returned.
    assert result["row_count"] is None


# ============================================================
# TEST 3: PLAIN-TEXT DOCUMENT EXTRACTION
# ============================================================

def test_text_extraction():
    """
    Verify that the text parser extracts readable content.

    Scenario:
        A text file contains a business name.

    Expected:
        status = success
        extracted text contains "Example Transport"

    This confirms that text evidence is available
    for the subsequent AI extraction process.
    """

    # Create sample text content as bytes.
    content = b"Business Name: Example Transport LLC"

    # Parse the simulated text attachment.
    result = parse_txt("application.txt", content)

    # Confirm that text decoding succeeded.
    assert result["status"] == "success"

    # Confirm that the expected business information
    # appears in the extracted evidence.
    assert "Example Transport" in result["sources"][0]["text"]


# ============================================================
# TEST 4: BROKER EMAIL EVIDENCE EXTRACTION
# ============================================================

def test_email_source():
    """
    Verify that pasted broker email text is processed
    as a separate evidence source.

    Scenario:
        A broker email states an operating radius
        of 150 miles.

    Expected:
        status = success
        source location = Email body

    This allows the underwriting system to identify
    the email as the source of extracted information.
    """

    # Simulate broker email text entered in Streamlit.
    result = parse_broker_email(
        "Operating Radius: 150 miles"
    )

    # Confirm that the email was processed successfully.
    assert result["status"] == "success"

    # Confirm that the source is identified as the email body.
    assert result["sources"][0]["location"] == "Email body"