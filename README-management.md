# Chayannito 26 - Registrants Management UI

A comprehensive web-based management system for handling registrants in the Chayannito 26 verification system.

## Features

### 🎯 Core Functionality
- **CRUD Operations**: Complete Create, Read, Update, Delete functionality for registrants
- **Immediate Persistence**: All changes are saved instantly to `registrants.json`
- **Auto-generated IDs**: Registration IDs are automatically generated based on group and gender
- **Live Verification Links**: Direct links to verification pages for each registrant

### 📊 Smart Organization
- **Group Classification**: Registrants organized by subject groups:
  - 🎨 **Arts (AR)** - Creative and liberal arts students
  - 🔬 **Science (SC)** - Science and technology students  
  - 💼 **Commerce (CO)** - Business and commerce students
- **Gender Segregation**: Within each group, registrants are separated by gender with visual indicators
- **Statistics Dashboard**: Real-time stats showing totals, payments, and active/revoked counts

### 🎨 Intuitive Design
- **Visual Cues**: 
  - Colored dots for gender identification (🔵 Male, 🟣 Female)
  - Group emojis for quick recognition
  - Status indicators for revoked registrations
- **Responsive Layout**: Works seamlessly on desktop and mobile devices
- **Beautiful UI**: Modern design using Tailwind CSS with smooth animations

### 🛡️ Robust Features
- **Form Validation**: Comprehensive client-side and server-side validation
- **Error Handling**: Graceful error handling with user-friendly messages
- **Confirmation Dialogs**: Safety confirmations for destructive actions
- **Auto-preview**: Registration ID preview while filling forms

## Quick Start

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Access
- Open your browser to `http://localhost:5000`
- Start managing registrants immediately!

## File Structure

```
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── registrants.json               # Data storage (auto-managed)
└── templates/
    ├── base.html                  # Base template with navigation
    ├── index.html                 # Main dashboard
    ├── add_registrant.html        # Add new registrant form
    └── edit_registrant.html       # Edit existing registrant form
```

## Usage

### Adding Registrants
1. Click "Add Registrant" in the navigation
2. Fill out the comprehensive form with:
   - Personal details (name, roll number)
   - Group and gender selection
   - Contact information (email, phone)
   - Payment details
   - Parts availability (T-Shirt, Food, Gift)
   - Referral information
3. Registration ID is auto-generated based on group and gender
4. Data is immediately saved to disk

### Managing Registrants
- **View**: Click "View" to see the live verification page
- **Edit**: Modify any registrant details, including revocation status
- **Delete**: Remove registrants with confirmation prompts
- **Statistics**: Monitor real-time dashboard statistics

### Data Format
Each registrant contains:
```json
{
  "name": "Student Name",
  "roll": "1202425010276",
  "gender": "Male",
  "registration_date": "11 September 2025",
  "registration_id": "SC-B-0001",
  "photo": "",
  "revoked": false,
  "referred_by": "",
  "paid": 1200,
  "email": "student@example.com",
  "phone": "01XXXXXXXXX",
  "parts_available": ["T-Shirt", "Food", "Gift"]
}
```

## Integration

This management UI integrates seamlessly with the existing verification system:
- **Shared Data**: Uses the same `registrants.json` file as `generate_verifications.py`
- **Compatible URLs**: Verification links use the same ID-to-filename conversion
- **Consistent Structure**: Maintains all existing data fields and formats

## Development

The application is built with:
- **Backend**: Flask (Python web framework)
- **Frontend**: Tailwind CSS for styling
- **Data Storage**: JSON file for simplicity and compatibility
- **Templating**: Jinja2 for dynamic content

## Security Notes

- This is a development server - use a production WSGI server for deployment
- The application handles form validation and data sanitization
- File operations include error handling and rollback capabilities

---

Built with ❤️ for Chayannito 26

Notes:
- When generating the master verified list, the "Referred By" column will attempt to resolve the value by registration ID, roll, or name and link to the referer's page. If no matching registrant is found, the original text is shown as plain text (no hyperlink). If the field is empty, an em-dash (—) will be displayed.