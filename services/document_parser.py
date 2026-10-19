# ============================================================
# IMPORTS
# ============================================================

# csv is used to read and process vehicle schedule CSV files.
import csv

# io allows us to treat decoded CSV text as a file-like object.
import io

# PyMuPDF is used to extract selectable text from PDF documents.
import pymupdf


# ============================================================
# 1. PDF DOCUMENT PARSER
# ============================================================

def parse_pdf(filename: str, file_bytes: bytes) -> dict:
    """
    Extract selectable text from a PDF document.

    Each page is stored as a separate evidence source so that
    the underwriter can trace extracted information to its
    original page.

    Args:
        filename: Name of the uploaded PDF file.
        file_bytes: Binary content of the uploaded PDF.

    Returns:
        Dictionary containing document status, extracted
        sources, and any parsing errors.
    """

    # Store successfully extracted page text.
    sources = []

    # Store parsing errors or pages without selectable text.
    errors = []

    try:
        # Open the uploaded PDF directly from memory.
        # No temporary file needs to be created.
        with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:

            # Process each page independently.
            # Page numbering begins at 1 for readability.
            for page_number, page in enumerate(pdf, start=1):

                # Extract selectable text and remove outer whitespace.
                text = page.get_text("text").strip()

                if text:
                    # Preserve the filename, page number, and text.
                    sources.append({
                        "filename": filename,
                        "location": f"Page {page_number}",
                        "text": text,
                    })
                else:
                    # Record pages that do not contain selectable text.
                    # For example, a scanned PDF may require OCR.
                    errors.append(
                        f"{filename}, page {page_number}: no selectable text"
                    )

        # Determine whether parsing was complete or partial.
        #
        # success    = Text was extracted without page errors.
        # partial    = Some text was extracted, but errors exist.
        # unreadable = No selectable text was extracted.
        status = "success" if sources and not errors else (
            "partial" if sources else "unreadable"
        )

    except Exception as exc:
        # Handle PDF opening or parsing failures.
        status = "failed"
        errors.append(f"PDF parsing failed: {exc}")

    return {
        "filename": filename,
        "file_type": "pdf",
        "status": status,
        "sources": sources,
        "errors": errors,
    }


# ============================================================
# 2. CSV DOCUMENT PARSER
# ============================================================

def parse_csv(filename: str, file_bytes: bytes) -> dict:
    """
    Parse CSV documents such as commercial vehicle schedules.

    Preserves the original CSV row references and counts
    nonempty data records.

    Args:
        filename: Name of the uploaded CSV file.
        file_bytes: Binary content of the CSV.

    Returns:
        Dictionary containing headers, rows, record count,
        evidence sources, and parsing status.
    """

    # Store evidence extracted from each nonempty CSV row.
    sources = []

    # Store errors encountered during CSV parsing.
    errors = []

    # Store parsed vehicle schedule records.
    rows = []

    try:
        # Decode the CSV using UTF-8.
        # utf-8-sig also handles files containing a UTF-8 BOM.
        content = file_bytes.decode("utf-8-sig")

        # Convert the CSV text into a file-like object.
        # DictReader maps each column header to its row value.
        reader = csv.DictReader(io.StringIO(content))

        # Reject CSV files without a header row.
        if not reader.fieldnames:
            raise ValueError("CSV header is missing")

        # Reject empty column header names.
        if None in reader.fieldnames:
            raise ValueError("CSV contains an empty column header")

        # Preserve the original CSV column names.
        headers = list(reader.fieldnames)

        # Process each CSV data record.
        for row in reader:

            # DictReader uses a None key when a row contains
            # more values than there are column headers.
            if None in row:
                raise ValueError("CSV row has more columns than the header")

            # Ignore completely empty records.
            if all(
                value is None or not str(value).strip()
                for value in row.values()
            ):
                continue

            # Store the valid, nonempty record.
            rows.append(row)

            # Convert the row into readable evidence text.
            # Example: vehicle_id: V001, make: Ford
            excerpt = ", ".join(
                f"{key}: {value}"
                for key, value in row.items()
            )

            # Preserve the physical CSV line number.
            # This helps reviewers locate the original record.
            sources.append({
                "filename": filename,
                "location": f"CSV row {reader.line_num}",
                "text": excerpt,
            })

        # CSV parsing completed without a detected error.
        status = "success"

    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        # Capture decoding, formatting, or validation failures.
        status = "failed"
        errors.append(f"CSV parsing failed: {exc}")

        # Clear the header information when parsing fails.
        headers = []

    return {
        "filename": filename,
        "file_type": "csv",
        "status": status,
        "headers": headers,
        "rows": rows,

        # Only expose a usable record count when parsing succeeds.
        "row_count": len(rows) if status == "success" else None,

        "sources": sources,
        "errors": errors,
    }


# ============================================================
# 3. TEXT DOCUMENT PARSER
# ============================================================

def parse_txt(filename: str, file_bytes: bytes) -> dict:
    """
    Decode plain-text attachments.

    Text documents may contain broker information,
    business details, or other submission evidence.
    """

    try:
        # Decode text using UTF-8 and remove outer whitespace.
        text = file_bytes.decode("utf-8-sig").strip()

        return {
            "filename": filename,
            "file_type": "txt",

            # Empty text files are considered unreadable.
            "status": "success" if text else "unreadable",

            # Store the entire text body as one evidence source.
            "sources": [{
                "filename": filename,
                "location": "Text body",
                "text": text,
            }] if text else [],

            # Report an error when the text file is empty.
            "errors": [] if text else ["Text file is empty"],
        }

    except UnicodeDecodeError as exc:
        # Handle files that cannot be decoded as UTF-8.
        return {
            "filename": filename,
            "file_type": "txt",
            "status": "failed",
            "sources": [],
            "errors": [f"Text decoding failed: {exc}"],
        }


# ============================================================
# 4. BROKER EMAIL PARSER
# ============================================================

def parse_broker_email(email_text: str) -> dict:
    """
    Process broker email text pasted into the application.

    The email is treated as a separate evidence source,
    allowing its information to be compared with uploaded
    application documents.
    """

    # Remove leading and trailing whitespace.
    text = email_text.strip()

    return {
        "filename": "broker_email",
        "file_type": "email",

        # Mark the email as readable when it contains text.
        "status": "success" if text else "unreadable",

        # Preserve the email body as source evidence.
        "sources": [{
            "filename": "broker_email",
            "location": "Email body",
            "text": text,
        }] if text else [],

        "errors": [],
    }


# ============================================================
# 5. COMPLETE SUBMISSION PARSER
# ============================================================

def parse_submission(uploaded_files, broker_email: str) -> dict:
    """
    Process all documents belonging to one submission packet.

    Responsibilities:
    1. Identify uploaded file types.
    2. Call the appropriate document parser.
    3. Collect extracted evidence.
    4. Build an attachment inventory.
    5. Process pasted broker email separately.

    Each call processes only the files and email provided
    for that particular submission.
    """

    # Store the parsed results of individual documents.
    documents = []

    # Store all extracted evidence across the submission.
    evidence = []

    # Store attachment metadata and processing status.
    inventory = []

    # Process each uploaded document independently.
    for uploaded_file in uploaded_files:

        # Retrieve the original uploaded filename.
        filename = uploaded_file.name

        # Determine file type from the filename extension.
        extension = filename.rsplit(".", 1)[-1].lower()

        # Read uploaded file contents into memory.
        file_bytes = uploaded_file.getvalue()

        # Route the document to the correct parser.
        if extension == "pdf":
            document = parse_pdf(filename, file_bytes)

        elif extension == "csv":
            document = parse_csv(filename, file_bytes)

        elif extension == "txt":
            document = parse_txt(filename, file_bytes)

        else:
            # Unsupported formats are reported as failed.
            document = {
                "filename": filename,
                "file_type": extension,
                "status": "failed",
                "sources": [],
                "errors": ["Unsupported file type"],
            }

        # Store the complete document parsing result.
        documents.append(document)

        # Add the document's evidence to the submission.
        evidence.extend(document["sources"])

        # Record the attachment's processing status.
        inventory.append({
            "filename": filename,
            "file_type": document["file_type"],
            "status": document["status"],
            "errors": document["errors"],
        })

    # Process the pasted broker email if one was provided.
    if broker_email.strip():

        # Treat the email as an independent document.
        email_document = parse_broker_email(broker_email)

        # Add the email to the parsed document collection.
        documents.append(email_document)

        # Add email text to the overall evidence collection.
        evidence.extend(email_document["sources"])

    # Return the complete parsed submission.
    # This result is used by the AI extraction service
    # and displayed in the Streamlit application.
    return {
        "documents": documents,
        "evidence": evidence,
        "attachment_inventory": inventory,
    }