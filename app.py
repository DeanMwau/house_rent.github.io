from flask import Flask, render_template, request, redirect, session, flash
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import base64
import os
from helpers import login_required, create_db

app = Flask(__name__)

# Set secret key for session management and flashing messages
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Call the function to create the database if it doesn't exist
create_db()

# Owner routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # Get form data
        username = request.form.get("username")
        number = request.form.get("number")
        password = request.form.get("password")
        confirmation =request.form.get("confirmation")
        role = request.form.get("role")

        # Validate form data
        if not username or not number or not password or not confirmation or not role: 
            flash("All fields are required.", "danger")
            return render_template('register.html')
        
        if confirmation != password:
            flash("Passwords do not match", "danger")
            return render_template('register.html')
        
        if role not in ["tenant", "owner"]:
            flash("Invalid role selected", "danger")
            return render_template('register.html')
        
        #Hash the password
        hashed_password = generate_password_hash(password)
        
        # Connect to the database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Determine the table based on the role
            table = "tenants" if role == "tenant" else "property_owners"

            # Check if username already exists in the database
            row = cursor.execute(
                "SELECT * FROM {} WHERE username = ?".format(
                    table), (username,)
            ).fetchone()

            if row:
                flash("Username already exists", "danger") 
                return render_template('register.html')   

            # Insert the new owner into the database after hashing their password
            cursor.execute("INSERT INTO {} (username, number, hash) VALUES(?, ?, ?)".format(
                table), 
                (username, number, hashed_password),
            )
            conn.commit()

        flash("Registered successfully! Kindly log in.", "success")   
        return render_template("login.html")
    
    # If the method was GET
    return render_template('register.html')


@app.route("/login", methods= ["GET", "POST"])
def login():
    # Forget users who had logged in earlier
    session.clear()

    # Owner reached route via POST
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            flash("Must provide username", "danger")
            return render_template("login.html")
        
        # Ensure password was submitted
        elif not password: 
            flash("Must provide password", "danger")
            return render_template("login.html")
        
        try:
            # Connect to database
            with sqlite3.connect("rentals.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Query both `tenants` and `property_owners` tables for the user
                tenant = cursor.execute("SELECT * FROM tenants WHERE username = ?", (username,)).fetchone()
                owner = cursor.execute("SELECT * FROM property_owners WHERE username = ?", (username,)).fetchone()

                # Validate tenant credentials
                if tenant and check_password_hash(tenant["hash"], password):
                    session["user_id"] = tenant["id"]
                    session["role"] = "tenant"
                    return redirect("/tenant_dashboard")
                
                # Validate owner credentials
                elif owner and check_password_hash(owner["hash"], password):
                    session["user_id"] = owner["id"]
                    session["role"] = "owner"
                    return redirect("/owner_dashboard")              

                # If no match, flash an error
                flash("Invalid username and/or password. Ensure you have created an account", "danger")
                return render_template("login.html")
        
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            return redirect("/login")
                                
    # Render the login page if the request method is GET
    return render_template("login.html")


@app.route("/owner_dashboard")
@login_required
def owner_dashboard():
    try:
        owner_id = session.get("user_id")

        # Connect to database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get apartments owned by the user
            cursor.execute("""
                SELECT id, title, description, rent, location FROM apartments WHERE owner_id = ?
            """, (owner_id,))
            apartments = cursor.fetchall()

            # Fetch images for each apartment
            apartments_with_images = []
            for apartment in apartments:

                # Fetch images for each apartment
                cursor.execute("""
                    SELECT image_blob FROM apartment_images WHERE apartment_id = ?
                """, (apartment["id"],))
                images = cursor.fetchall()

                # Convert binary image data to base64 strings
                image_base64_list = [
                            base64.b64encode(image["image_blob"]).decode('utf-8') for image in images
                        ]
            
                apartments_with_images.append({
                    "id": apartment["id"],
                    "title": apartment["title"],
                    "description": apartment["description"],
                    "rent": apartment["rent"],
                    "location": apartment["location"],
                    "images": image_base64_list,

                }) 
        return render_template('owner_dashboard.html', apartments=apartments_with_images)

    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return render_template("login.html")


@app.route("/tenant_dashboard")
@login_required
def tenant_dashboard():
    try:
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Fetch apartments and their images
            cursor.execute("""
                SELECT apartments.id AS apartment_id, 
                        apartments.title, 
                        apartments.description, 
                        apartments.rent, 
                        apartments.location, 
                        apartment_images.image_blob 
                FROM apartments 
                LEFT JOIN apartment_images ON apartments.id = apartment_images.apartment_id
            """)
            rows = cursor.fetchall()

            # Group images by apartments
            apartments = {}
            for row in rows:
                apartment_id = row["apartment_id"]
                if apartment_id not in apartments:
                    apartments[apartment_id] = {
                         "id": apartment_id,
                        "title": row["title"],
                        "description": row["description"],
                        "rent": row["rent"],
                        "location": row["location"],
                        "images": [],
                    }

                # Add image if it exists
                if row["image_blob"]:
                    apartments[apartment_id]["images"].append(
                        base64.b64encode(row["image_blob"]).decode("utf-8")
                    )

            # Convert dictionary to list for rendering
            apartments_list = list(apartments.values())
        return render_template('apartments.html', apartments=apartments_list)

    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return render_template("login.html")



@app.route("/add_apartment", methods= ["GET", "POST"])
@login_required
def add_apartment():
    if request.method == "POST":
        owner_id = session.get("user_id")

        title = request.form.get("title")
        description = request.form.get("description")
        rent = request.form.get("rent")
        location = request.form.get("location")
        images = request.files.getlist("images")

        # Validate inputs
        if not title or not description or not rent or not location:
            flash("All fields are required", "danger")
            return render_template("add_apartment.html")
                
        if not images or all(image.filename == '' for image in images):
            flash("At least one image is required", "danger")
            return render_template("add_apartment.html")

        try:
            with sqlite3.connect("rentals.db") as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()

                # Insert apartment details
                cursor.execute("""
                INSERT INTO apartments (owner_id, title, description, rent, location)
                VALUES (?, ?, ?, ?, ?)
            """, (owner_id, title, description, float(rent), location))
                apartment_id = cursor.lastrowid
                
                # Insert images into the aprtment_images table
                for image in images:
                    image_blob = image.read()
                    cursor.execute("""
                        INSERT INTO apartment_images (apartment_id, image_blob)
                        VALUES (?, ?)
                    """, (apartment_id, image_blob))
                
            conn.commit()

            # Flash a success message
            flash("Apartment added successfully!", "success")
            return redirect("/owner_dashboard")
        
        except Exception as e:
            # Flash an error message if there's an issue with the database
            flash(f"An error occurred: {e}", "danger")
            return render_template("add_apartment.html")
    
    return render_template('add_apartment.html')


@app.route("/change_password", methods= ["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":

        # Get the form data
        username = request.form.get("username")
        oldpassword = request.form.get("oldpassword")
        newpassword = request.form.get("newpassword")
        confirmnewpassword = request.form.get("confirmnewpassword")
        role = request.form.get("role")

        # Validate form data
        if not username or not oldpassword or not newpassword or not confirmnewpassword:
            flash("All fields are required.", "danger")
            return render_template("change_password.html")

        if newpassword != confirmnewpassword:
            flash("New passwords do not match.", "danger")
            return render_template("change_password.html")
        
        try:
            # Determine the user's table based on their role from the session
            role = session.get("role")
            table = "tenants" if role == "tenant" else "property_owners"

            # Connect to the database
            with sqlite3.connect("rentals.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Check if the user exists
                cursor.execute(f"SELECT * FROM {table} WHERE username = ?", (username,))
                user = cursor.fetchone()

                if not user:
                    flash("User not found.", "danger")
                    return render_template("change_password.html")
                
                # Verify the old password
                if not check_password_hash(user['hash'], oldpassword):
                    flash("Old password is incorrect.", "danger")
                    return render_template("change_password.html")
                
                # Hash the new password
                hashed_new_password = generate_password_hash(newpassword) 

                # Update the password in the database
                cursor.execute(f"UPDATE {table} SET hash = ? WHERE username = ?", (hashed_new_password, username))
                conn.commit()

            flash("Password changed successfully!", "success")
            return redirect("/login")
        
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            return render_template("change_password.html")

    return render_template("change_password.html")


@app.route("/edit_apartment/<int:apartment_id>", methods= ["GET", "POST"])
@login_required
def edit_apartment(apartment_id):
    try:
        owner_id = session.get("user_id")

        # Connect to the database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Fetch the apartment details
            cursor.execute("""
                SELECT * FROM apartments WHERE id = ? AND owner_id = ?
            """, (apartment_id, owner_id))
            apartment = cursor.fetchone()

            # If no apartment is found, redirect to the dashboard
            if not apartment:
                flash("Apartment not found or you don't have permission to edit this apartment.", "danger")
                return redirect("/owner_dashboard")
        

        if request.method == "POST":

            # Get form data
            title = request.form.get("title")
            description = request.form.get("description")
            rent = request.form.get("rent")
            location = request.form.get("location")
            images = request.files.getlist("images")

            # Validate inputs
            if not title or not description or not rent or not location:
                flash("All fields are required", "danger")
                return redirect(f"/edit_apartment/{apartment_id}")
        
            try:
                    # Update apartment details
                    with sqlite3.connect("rentals.db") as conn:
                        conn.row_factory = sqlite3.Row
                        conn.execute("PRAGMA foreign_keys = ON")
                        cursor = conn.cursor()

                        # Update details on database
                        cursor.execute("""
                        UPDATE apartments
                        SET title = ?, description = ?, rent = ?, location = ?
                        WHERE id = ? AND owner_id = ?
                    """, (title, description, float(rent), location, apartment_id, owner_id))                        

                        # If new images are uploaded, replace existing images
                        if images and any(image.filename != '' for image in images):
                            cursor.execute("DELETE FROM apartment_images WHERE apartment_id = ?", (apartment_id,))
                            for image in images:
                                image_blob = image.read()
                                cursor.execute("""
                                    INSERT INTO apartment_images (apartment_id, image_blob)
                                    VALUES (?, ?)
                                """, (apartment_id, image_blob))
                        
                        conn.commit()
                    
                    flash("Apartment updated successfully!", "success")
                    return redirect("/owner_dashboard")
            
            except Exception as e:
                flash(f"An error occurred while updating the apartment: {e}", "danger")
                return redirect(f"/edit_apartment/{apartment_id}")
            
        if request.method == "GET":

                # Render the edit form with the current apartment details
                with sqlite3.connect("rentals.db") as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Fetch existing images for the apartment
                    cursor.execute("""
                        SELECT image_blob FROM apartment_images WHERE apartment_id = ?
                    """, (apartment_id,))
                    images = cursor.fetchall()

                    # Convert binary image data to base64 for rendering
                    image_base64_list = [
                        base64.b64encode(image["image_blob"]).decode('utf-8') for image in images
                    ]
                
                return render_template("edit_apartment.html", apartment=apartment, images=image_base64_list)
        
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/owner_dashboard")
    
    
@app.route("/delete_apartment/<int:apartment_id>", methods= ["POST"])
@login_required
def delete_apartment(apartment_id):
    try:
        owner_id = session.get("user_id")

        # Connect to the database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Delete details associated with the id
            cursor.execute("DELETE FROM apartments WHERE id = ? AND owner_id = ?", (apartment_id, owner_id,))
            cursor.execute("DELETE FROM apartment_images WHERE apartment_id = ?", (apartment_id,))
            conn.commit()

            flash("Apartment deleted successfully!", "success")
            return redirect("/owner_dashboard")
    
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/owner_dashboard")   
    

@app.route("/search", methods= ["GET", "POST"])
def search():  
    tenant_id = session.get("user_id")  
    location = request.form.get("query") if request.method == "POST" else request.args.get("query")

    # Validate user input
    if not location:
        flash("Kindly enter the location", "danger")
        return redirect("/")  
          
    try:    
        # Connect and query the database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT apartments.id AS apartment_id, 
                        apartments.title, 
                        apartments.description, 
                        apartments.rent, 
                        apartments.location, 
                        apartment_images.image_blob 
                FROM apartments 
                LEFT JOIN apartment_images ON apartments.id = apartment_images.apartment_id WHERE apartments.location like ?
            """, ('%' + location + '%',))

            rows = cursor.fetchall()
        
        # Organize results into a dictionary grouped by apartments
        apartments = {}
        for row in rows:
            apartment_id = row["apartment_id"]
            if apartment_id not in apartments:
                apartments[apartment_id] = {
                    "id": apartment_id,
                    "title": row["title"],
                    "description": row["description"],
                    "rent": row["rent"],
                    "location": row["location"],
                    "images": [],
                }

            if row["image_blob"]:
                apartments[apartment_id]["images"].append(base64.b64encode(row["image_blob"]).decode("utf-8"))

        # If no apartments are found, notify the user
        if not rows:
            flash("No apartments found in the specified location.", "info")
            return redirect("/")
        
        # Determine if the user is a tenant (example logic; replace with your actual user role-checking logic)
        is_tenant = session.get("user_role") == "tenant"
        
        # Render the search results page
        return render_template("apartments_search.html", apartments=list(apartments.values()), is_tenant=is_tenant)             

    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/") 

    
@app.route("/rent_apartment/<int:apartment_id>", methods=["POST"])
def rent_apartment(apartment_id):
    tenant_id = session.get("user_id")

    # Check if the user is logged in
    if not tenant_id:
        flash("You need to log in first to rent an apartment.", "danger")
        return redirect("/login")
    
    try:
            # Connect to the database and record the request
            with sqlite3.connect("rentals.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                 # Check for duplicate rental requests
                cursor.execute("""
                    SELECT id FROM rent_requests 
                    WHERE tenant_id = ? AND apartment_id = ?
                """, (tenant_id, apartment_id))
                existing_request = cursor.fetchone()

                if existing_request:
                    flash("You have already submitted a rental request for this apartment.", "danger")
                    return redirect("/tenant_dashboard")
                
                # Insert the rental request
                cursor.execute("""
                    SELECT number FROM tenants 
                    WHERE id = ?
                """, (tenant_id,))
                tenant_number = cursor.fetchone()
                number = tenant_number[0]

                cursor.execute("""
                INSERT INTO rent_requests (tenant_id, tenant_number, apartment_id, status)
                VALUES (?, ?, ?, ?)
                """, (tenant_id, number, apartment_id, "pending"))
                conn.commit()

                flash("Rental request submitted!", "success")
                return redirect("/rented_apartment")
                    
    except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            return redirect("/tenant_dashboard")
    

@app.route("/rented_apartment", methods= ["GET"])
@login_required
def rented_apartment():
    tenant_id = session.get("user_id") 
    try:
        # Connect to the database and record the request
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            apartments = cursor.execute("""
                SELECT 
                    apartments.id AS apartment_id, 
                    apartments.title, 
                    apartments.description,
                    apartments.rent,
                    apartments.location,
                    apartment_images.image_blob,
                    rent_requests.status
                FROM rent_requests
                JOIN apartments ON rent_requests.apartment_id = apartments.id
                LEFT JOIN apartment_images ON apartments.id = apartment_images.apartment_id
                WHERE rent_requests.tenant_id = ?
                ORDER BY rent_requests.id;                                                 
            """, (tenant_id,)).fetchall()

            # Convert data to a format suitable for HTML rendering
            rented_apartments = {}
            for apartment in apartments:
                apartment_id = apartment["apartment_id"]
                if apartment_id not in rented_apartments:
                    rented_apartments[apartment_id] = {
                        "id": apartment_id,
                        "title": apartment["title"],
                        "description": apartment["description"],
                        "rent": apartment["rent"],
                        "location": apartment["location"],
                        "images": [],
                        "status": apartment["status"]
                    }
                
                # Append images if they exist
                if apartment["image_blob"]:
                    rented_apartments[apartment_id]["images"].append(
                        base64.b64encode(apartment["image_blob"]).decode("utf-8")
                    )

            rented_apartments_list = list(rented_apartments.values())
        return render_template("rented_apartment.html", apartments=rented_apartments_list)

    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/tenant_dashboard")
    

@app.route("/cancel_rent_request/<int:apartment_id>", methods= ["POST"])
@login_required
def cancel_rent_request(apartment_id):
    try:
        tenant_id = session.get("user_id")

        # Connect to the database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Delete details associated with the id
            cursor.execute("DELETE FROM rent_requests WHERE apartment_id = ? AND tenant_id = ?", (apartment_id, tenant_id,))
            conn.commit()

            flash("Request cancelled successfully!", "success")
            return redirect("/rented_apartment")
    
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/rented_apartment")


@app.route("/view_rent_requests", methods= ["GET"])
@login_required
def view_rent_requests():
    owner_id = session.get("user_id")

    try:
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get rental requests for the owner's apartments
            requests = cursor.execute("""
                SELECT
                    tenants.username AS tenant_username,
                    tenants.number AS tenant_number,
                    apartments.title AS apartment_title,
                    apartments.location AS apartment_location,
                    rent_requests.status AS request_status,
                    rent_requests.id AS request_id
                FROM 
                    rent_requests
                JOIN 
                    tenants ON rent_requests.tenant_id = tenants.id
                JOIN 
                    apartments ON rent_requests.apartment_id = apartments.id
                WHERE 
                    apartments.owner_id = ?
            """, (owner_id,)).fetchall()

        return render_template("view_rent_requests.html", requests=requests)
    
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/owner_dashboard")

@app.route("/change_request_status/<int:request_id>/<action>", methods=["POST"])
@login_required
def change_request_status(request_id, action):
    try:
        # Connect to the database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Retrieve current status
            cursor.execute("SELECT status FROM rent_requests WHERE id = ?", (request_id,))
            request = cursor.fetchone()

            if not request:
                flash("Request not found.", "danger")
                return redirect("/view_rent_requests")
            
            current_status = request["status"]

             # Only allow changes if the current status is pending
            if current_status != "pending":
                flash("Only pending requests can be approved or declined.", "warning")
                return redirect("/view_rent_requests")

            # Determine new status based on action
            if action == "approve":
                new_status = "approved"
            elif action == "decline":
                new_status = "declined"
            else:
                flash("Invalid action specified.", "danger")
                return redirect("/view_rent_requests")
            
            # Update the status in the database
            cursor.execute("UPDATE rent_requests SET status = ? WHERE id = ?", (new_status, request_id))
            conn.commit()

            flash(f"Request successfully {new_status}.", "success")
        
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")

    return redirect("/view_rent_requests")

@app.route("/enquire/<int:apartment_id>", methods=["GET", "POST"])
@login_required
def enquire(apartment_id):
    if request.method == "GET":
        try:
            # Fetch apartment details and owner info
            with sqlite3.connect("rentals.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT 
                        property_owners.number AS number,
                        apartments.id AS id,
                        apartments.title AS title
                    FROM 
                        property_owners
                    JOIN
                        apartments ON  apartments.owner_id = property_owners.id
                    WHERE 
                        apartments.id = ?
                """, (apartment_id,))

                apartment = cursor.fetchone()

                if not apartment:
                    flash("Apartment not found.", "danger")
                    return redirect("/tenant_dashboard")
                
                return render_template("enquire_form.html", apartment=apartment)
            
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            return redirect("/tenant_dashboard")
    
    if request.method == "POST":
        # Handle the enquiry form submission
        tenant_name = request.form.get("name")
        tenant_email = request.form.get("email")
        message = request.form.get("message")

        if not tenant_name or not tenant_email or not message:
            flash("All fields are required.", "danger")
            return redirect(f"/enquire/{apartment_id}")
        
        try:
            with sqlite3.connect("rentals.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Fetch the owner_id for the given apartment_id
                cursor.execute("SELECT owner_id FROM apartments WHERE id = ?", (apartment_id,))
                owner = cursor.fetchone()

                if not owner:
                    flash("Apartment not found.", "danger")
                    return redirect("/tenant_dashboard")

                owner_id = owner["owner_id"]

                # Insert enquiry into the `enquiries` table
                cursor.execute("""
                    INSERT INTO enquiries (tenant_name, tenant_email, message, apartment_id, owner_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (tenant_name, tenant_email, message, apartment_id, owner_id))

                conn.commit()
            
            flash("Your enquiry has been sent to the owner.", "success")
            return redirect("/tenant_dashboard")
        
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            return redirect("/tenant_dashboard")

@app.route("/view_enquiries", methods=["GET"])
@login_required
def view_enquiries():
    owner_id = session.get("user_id")

    try:
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Fetch enquiries for the logged-in owner
            cursor.execute("""
                SELECT 
                    enquiries.tenant_name, 
                    enquiries.tenant_email, 
                    enquiries.message, 
                    apartments.title AS apartment_title
                FROM enquiries
                JOIN apartments ON enquiries.apartment_id = apartments.id
                WHERE enquiries.owner_id = ?
            """, (owner_id,))
            enquiries = cursor.fetchall()

        return render_template("enquiries.html", enquiries=enquiries)
    
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/owner_dashboard")


@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html")


@app.route("/explore")
def explore():
    try:
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Fetch apartments and their images
            cursor.execute("""
                SELECT apartments.id AS apartment_id, 
                        apartments.title, 
                        apartments.description, 
                        apartments.rent, 
                        apartments.location, 
                        apartment_images.image_blob 
                FROM apartments 
                LEFT JOIN apartment_images ON apartments.id = apartment_images.apartment_id
            """)
            rows = cursor.fetchall()

            # Group images by apartments
            apartments = {}
            for row in rows:
                apartment_id = row["apartment_id"]
                if apartment_id not in apartments:
                    apartments[apartment_id] = {
                         "id": apartment_id,
                        "title": row["title"],
                        "description": row["description"],
                        "rent": row["rent"],
                        "location": row["location"],
                        "images": [],
                    }

                # Add image if it exists
                if row["image_blob"]:
                    apartments[apartment_id]["images"].append(
                        base64.b64encode(row["image_blob"]).decode("utf-8")
                    )

            # Convert dictionary to list for rendering
            apartments_list = list(apartments.values())
        return render_template('explore.html', apartments=apartments_list)

    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/")
    


@app.route("/reviews/<int:apartment_id>", methods=["GET", "POST"])
def reviews(apartment_id):
    try:
        # Get the logged-in tenant's ID
        tenant_id = session.get("user_id")

        # Connect to the database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Fetch apartment details for context
            cursor.execute("""
                SELECT id, title, location FROM apartments WHERE id = ?
            """, (apartment_id,))
            apartment = cursor.fetchone()

            if not apartment:
                flash("Apartment not found.", "danger")
                return redirect("/tenant_dashboard")

            # Fetch all reviews for the apartment
            cursor.execute("""
                SELECT reviews.id, reviews.text, reviews.rating, tenants.username, reviews.date
                FROM reviews 
                JOIN tenants ON reviews.tenant_id = tenants.id
                WHERE reviews.apartment_id = ?
                ORDER BY reviews.date DESC
            """, (apartment_id,))
            reviews = cursor.fetchall()

             # Fetch the tenant's review, if any
            cursor.execute("""
                SELECT id, text, rating FROM reviews 
                WHERE apartment_id = ? AND tenant_id = ?
            """, (apartment_id, tenant_id))
            tenant_review = cursor.fetchone()

            # Fetch ratings for this apartment to calculate the average rating
            cursor.execute("""
                SELECT rating FROM reviews WHERE apartment_id = ?
            """, (apartment_id,))
            ratings = cursor.fetchall()

            # Calculate the average rating if there are ratings
            if ratings:
                total_rating = sum([rating[0] for rating in ratings])
                average_rating = total_rating / len(ratings)
            else:
                average_rating = None  # No reviews yet

        # Handle POST request for adding a new review
        if request.method == "POST":
            # Ensure only logged in tenants can post a review  
            if not tenant_id:
                flash("You need to log in to perform this action.", "danger")
                return redirect(f"/reviews/{apartment_id}")
            
            text = request.form.get("text")
            rating = request.form.get("rating")
    
            # Validate input
            if not text or not rating:
                flash("Review text and rating are required.", "danger")
                return redirect(f"/reviews/{apartment_id}")
                    
            try:
                 # Insert the new review into the database
                with sqlite3.connect("rentals.db") as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    if tenant_review:

                        # Update existing review
                        cursor.execute("""
                            UPDATE reviews 
                            SET text = ?, rating = ?, date = datetime('now') 
                            WHERE id = ?
                        """, (text, int(rating), tenant_review["id"]))

                        flash("Your review has been updated successfully!", "success")

                    else:
                        # Add new review
                        cursor.execute("""
                            INSERT INTO reviews (apartment_id, tenant_id, text, rating, date)
                            VALUES (?, ?, ?, ?, datetime('now'))
                        """, (apartment_id, tenant_id, text, int(rating)))

                        flash("Your review has been added successfully!", "success")

                    conn.commit()

                return redirect(f"/reviews/{apartment_id}")
            
            except Exception as e:
                flash(f"An error occurred while adding the review: {e}", "danger")
                return redirect(f"/reviews/{apartment_id}")
        
        return render_template("reviews.html", reviews=reviews, apartment=apartment, tenant_review=tenant_review, average_rating=average_rating)
    
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/tenant_dashboard")
    

@app.route("/reviews/delete/<int:review_id>", methods=["POST"])
@login_required
def delete_review(review_id):
    try:
        # Get the logged-in tenant's ID
        tenant_id = session.get("user_id")  
        with sqlite3.connect("rentals.db") as conn:
            cursor = conn.cursor()

            # Check if the review exists and belongs to the tenant
            cursor.execute("""
                SELECT id FROM reviews WHERE id = ? AND tenant_id = ?
            """, (review_id, tenant_id))
            review = cursor.fetchone()

            if not review:
                flash("Review not found or unauthorized action.", "danger")
                return redirect("/tenant_dashboard")

            # Delete the review
            cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            conn.commit()
            flash("Review deleted successfully!", "success")

        return redirect(request.referrer or "/tenant_dashboard")

    except Exception as e:
        flash(f"An error occurred while deleting the review: {e}", "danger")
        return redirect("/tenant_dashboard")

@app.route("/reviews/edit/<int:review_id>", methods=["POST"])
@login_required
def edit_review(review_id):
    try:
        # Get tenant ID
        tenant_id = session.get("user_id")
        text = request.form.get("text")
        rating = request.form.get("rating")

        # Get the apartment_id from the form
        apartment_id = request.form.get("apartment_id") 

        if not text or not rating:
            flash("Review text and rating are required.", "danger")
            return redirect("/tenant_dashboard")

        # Update the review in the database
        with sqlite3.connect("rentals.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE reviews
                SET text = ?, rating = ?, date = datetime('now')
                WHERE id = ? AND tenant_id = ?
            """, (text, rating, review_id, tenant_id))
            conn.commit()

        flash("Review updated successfully!", "success")
        return redirect(f"/reviews/{apartment_id}")
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/tenant_dashboard")
    

@app.route("/view_reviews", methods=["GET"])
@login_required
def view_reviews():
    try:
        # Get the owner's ID from the session
        owner_id = session.get("user_id")
        
        if not owner_id:
            flash("You need to log in as an owner to access this page.", "danger")
            return redirect("/login")
        
        # Connect to the database
        with sqlite3.connect("rentals.db") as conn:
            conn.row_factory = sqlite3.Row  # Rows will now behave like dictionaries
            cursor = conn.cursor()

            # Fetch apartments owned by the owner
            cursor.execute("""
                SELECT id, title, location
                FROM apartments
                WHERE owner_id = ?
            """, (owner_id,))
            apartments = cursor.fetchall()
            if not apartments:
                flash("You don't own any apartments yet.", "info")
                return render_template("view_reviews.html", apartments=[])
            
            # Fetch reviews for those apartments
            cursor.execute("""
                SELECT 
                    reviews.id AS review_id, reviews.text, reviews.rating, reviews.date, 
                    reviews.apartment_id, tenants.username
                FROM reviews
                JOIN tenants ON reviews.tenant_id = tenants.id
                WHERE reviews.apartment_id IN (
                    SELECT id
                    FROM apartments
                    WHERE owner_id = ?
                )
                ORDER BY reviews.date DESC
            """, (owner_id,))
            reviews = cursor.fetchall()
        
        # Organize reviews by apartment
        reviews_by_apartment = {}
        for review in reviews:
            apartment_id = review["apartment_id"]
            if apartment_id not in reviews_by_apartment:
                reviews_by_apartment[apartment_id] = []
            reviews_by_apartment[apartment_id].append({
                "id": review["review_id"],
                "text": review["text"],
                "rating": review["rating"],
                "date": review["date"],
                "username": review["username"],
            })
        
        return render_template("view_reviews.html", apartments=apartments, reviews_by_apartment=reviews_by_apartment)
        
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect("/owner_dashboard")


@app.route("/logout")
def logout():
    # Forget any owner_id
    session.clear()

    # Redirect owner to login form
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)