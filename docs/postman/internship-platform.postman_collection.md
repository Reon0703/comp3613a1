{
  "info": {
    "_postman_id": "d7113500-7422-4c7b-8a38-ec76122ec10a",
    "name": "Internship Platform API Tests",
    "description": "Postman Collection v2.1 generated from docs/api-spec.md. Implemented JSON routes include POST /api/auth/register, POST /api/auth/login, POST /api/auth/logout, GET /api/me, and GET /api/users. Other business endpoints are proposed and their contract tests will fail with a 404 until implemented. Set the companyUsername/companyPassword collection variables to an existing company account. Run folders in order. Select PDF files in the form-data rows for application upload and replacement. Postman keeps the HttpOnly access_token cookie in its cookie jar after successful login.",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://0.0.0.0:5000",
      "type": "string"
    },
    {
      "key": "studentUsername",
      "value": "",
      "type": "string"
    },
    {
      "key": "studentEmail",
      "value": "",
      "type": "string"
    },
    {
      "key": "studentPassword",
      "value": "Student-Test-Password-123!",
      "type": "string"
    },
    {
      "key": "registrationCompanyUsername",
      "value": "",
      "type": "string"
    },
    {
      "key": "registrationCompanyEmail",
      "value": "",
      "type": "string"
    },
    {
      "key": "registrationCompanyPassword",
      "value": "Company-Test-Password-123!",
      "type": "string"
    },
    {
      "key": "companyUsername",
      "value": "company.demo",
      "type": "string"
    },
    {
      "key": "companyPassword",
      "value": "change-me",
      "type": "string"
    },
    {
      "key": "vacancyId",
      "value": "1",
      "type": "string"
    },
    {
      "key": "applicationId",
      "value": "1",
      "type": "string"
    },
    {
      "key": "documentId",
      "value": "1",
      "type": "string"
    },
    {
      "key": "vacancyDocumentId",
      "value": "1",
      "type": "string"
    },
    {
      "key": "fieldOfStudy",
      "value": "Technology",
      "type": "string"
    },
    {
      "key": "searchQuery",
      "value": "",
      "type": "string"
    },
    {
      "key": "educationLevel",
      "value": "Undergraduate",
      "type": "string"
    },
    {
      "key": "page",
      "value": "1",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "Implemented API - User listing",
      "description": "GET /api/users is implemented as a JSON API route.",
      "item": [
        {
          "name": "List users",
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/users",
            "description": "Implemented endpoint. Returns a list of users with id, username, and email."
          },
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns an array of public user fields', function () {",
                  "  const users = pm.response.json();",
                  "  pm.expect(users).to.be.an('array');",
                  "  if (users.length) {",
                  "    pm.expect(users[0]).to.have.all.keys('id', 'username', 'email');",
                  "  }",
                  "});"
                ]
              }
            }
          ]
        }
      ]
    },
    {
      "name": "Account API and student profile",
      "description": "Student and company registration, sign-in, and current-user routes are implemented. The student profile update request is still proposed. Registration creates unique accounts for each run; sign-in stores the access_token cookie in Postman's cookie jar.",
      "item": [
        {
          "name": "Register student",
          "event": [
            {
              "listen": "prerequest",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "const suffix = Date.now().toString();",
                  "pm.collectionVariables.set('studentUsername', 'postman_student_' + suffix);",
                  "pm.collectionVariables.set('studentEmail', 'postman_student_' + suffix + '@example.com');"
                ]
              }
            },
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('creates student account with HTTP 201', function () { pm.response.to.have.status(201); });",
                  "pm.test('returns the created student without a password', function () {",
                  "  const body = pm.response.json();",
                  "  pm.expect(body.user.username).to.eql(pm.collectionVariables.get('studentUsername'));",
                  "  pm.expect(body.user.email).to.eql(pm.collectionVariables.get('studentEmail'));",
                  "  pm.expect(body.user.role).to.eql('regular_user');",
                  "  pm.expect(body.user).not.to.have.property('password');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{studentUsername}}\",\n  \"email\": \"{{studentEmail}}\",\n  \"password\": \"{{studentPassword}}\",\n  \"role\": \"regular_user\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/auth/register",
            "description": "Implemented JSON endpoint. A timestamped username/email is generated before each request."
          }
        },
        {
          "name": "Register company",
          "event": [
            {
              "listen": "prerequest",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "const suffix = Date.now().toString();",
                  "pm.collectionVariables.set('registrationCompanyUsername', 'postman_company_' + suffix);",
                  "pm.collectionVariables.set('registrationCompanyEmail', 'postman_company_' + suffix + '@example.com');"
                ]
              }
            },
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('creates company account with HTTP 201', function () { pm.response.to.have.status(201); });",
                  "pm.test('returns the created company without a password', function () {",
                  "  const body = pm.response.json();",
                  "  pm.expect(body.user.username).to.eql(pm.collectionVariables.get('registrationCompanyUsername'));",
                  "  pm.expect(body.user.email).to.eql(pm.collectionVariables.get('registrationCompanyEmail'));",
                  "  pm.expect(body.user.role).to.eql('company');",
                  "  pm.expect(body.user).not.to.have.property('password');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{registrationCompanyUsername}}\",\n  \"email\": \"{{registrationCompanyEmail}}\",\n  \"password\": \"{{registrationCompanyPassword}}\",\n  \"role\": \"company\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/auth/register",
            "description": "Implemented JSON endpoint. A timestamped company username/email is generated before each request."
          }
        },
        {
          "name": "Login student",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('logs in with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns the signed-in student identity', function () {",
                  "  const user = pm.response.json().user;",
                  "  pm.expect(user.username).to.eql(pm.collectionVariables.get('studentUsername'));",
                  "  pm.expect(user.role).to.eql('regular_user');",
                  "  pm.expect(pm.response.headers.get('Set-Cookie') || '').to.include('access_token=');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{studentUsername}}\",\n  \"password\": \"{{studentPassword}}\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/auth/login",
            "description": "Implemented JSON endpoint. A successful response sets an HttpOnly access_token cookie."
          }
        },
        {
          "name": "Login rejects invalid credentials",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 401', function () { pm.response.to.have.status(401); });",
                  "pm.test('returns the invalid-credentials error', function () {",
                  "  pm.expect(pm.response.json().detail).to.eql('Incorrect username or password');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{studentUsername}}\",\n  \"password\": \"definitely-wrong\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/auth/login",
            "description": "Negative test for the implemented JSON endpoint."
          }
        },
        {
          "name": "Get current user",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns the authenticated student profile', function () {",
                  "  const user = pm.response.json();",
                  "  pm.expect(user.username).to.eql(pm.collectionVariables.get('studentUsername'));",
                  "  pm.expect(user.role).to.eql('regular_user');",
                  "  pm.expect(user).not.to.have.property('password');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/me",
            "description": "Implemented JSON endpoint. Requires the student access_token cookie."
          }
        },
        {
          "name": "Update student profile",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('updates profile with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('confirms the student profile update', function () {",
                  "  pm.expect(pm.response.json().message).to.eql('student profile updated');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "PUT",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"first_name\": \"Postman\",\n  \"last_name\": \"Student\",\n  \"email\": \"{{studentEmail}}\",\n  \"education_level\": \"Undergraduate\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/students/me",
            "description": "Proposed JSON endpoint. Requires a student access_token cookie."
          }
        }
      ]
    },
    {
      "name": "Proposed API - Company vacancy management",
      "description": "Proposed JSON routes. Configure companyUsername and companyPassword with an existing company account before running this folder.",
      "item": [
        {
          "name": "Login company",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('logs in with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns a company account', function () {",
                  "  pm.expect(pm.response.json().user.role).to.eql('company');",
                  "  pm.expect(pm.response.headers.get('Set-Cookie') || '').to.include('access_token=');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{companyUsername}}\",\n  \"password\": \"{{companyPassword}}\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/auth/login",
            "description": "Sign in as the configured company account. Successful login replaces the Postman cookie for this host."
          }
        },
        {
          "name": "Update company profile",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('updates profile with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('confirms the company profile update', function () {",
                  "  pm.expect(pm.response.json().message).to.eql('company profile updated');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "PUT",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"company_name\": \"Postman Test Company\",\n  \"email\": \"postman-company@example.test\",\n  \"phone\": \"555-0100\",\n  \"location\": \"Port of Spain\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/companies/me",
            "description": "Proposed JSON endpoint. Requires a company access_token cookie."
          }
        },
        {
          "name": "Create published vacancy",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('creates vacancy with HTTP 201', function () { pm.response.to.have.status(201); });",
                  "pm.test('returns a published vacancy', function () {",
                  "  const vacancy = pm.response.json();",
                  "  pm.expect(vacancy.title).to.eql('Postman API Test Internship');",
                  "  pm.expect(vacancy.status).to.eql('Published');",
                  "  pm.expect(vacancy.is_published).to.eql(true);",
                  "  pm.collectionVariables.set('vacancyId', String(vacancy.id));",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "formdata",
              "formdata": [
                {
                  "key": "title",
                  "value": "Postman API Test Internship",
                  "type": "text"
                },
                {
                  "key": "description",
                  "value": "Created by the Postman API contract collection.",
                  "type": "text"
                },
                {
                  "key": "location",
                  "value": "Port of Spain",
                  "type": "text"
                },
                {
                  "key": "field_of_study",
                  "value": "{{fieldOfStudy}}",
                  "type": "text"
                },
                {
                  "key": "status",
                  "value": "Published",
                  "type": "text"
                },
                {
                  "key": "vacancy_image",
                  "type": "file",
                  "src": ""
                }
              ]
            },
            "url": "{{baseUrl}}/api/company/vacancies",
            "description": "Proposed JSON endpoint using multipart/form-data. The image is optional; select a file in Postman or remove the vacancy_image form row."
          }
        },
        {
          "name": "List company vacancies",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns this company vacancy', function () {",
                  "  const vacancies = pm.response.json();",
                  "  pm.expect(vacancies).to.be.an('array');",
                  "  pm.expect(vacancies.some(function (item) { return String(item.id) === pm.collectionVariables.get('vacancyId'); })).to.eql(true);",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/company/vacancies",
            "description": "Proposed JSON endpoint. Requires a company access_token cookie."
          }
        },
        {
          "name": "Update vacancy",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('updates vacancy with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns the updated vacancy', function () {",
                  "  const vacancy = pm.response.json();",
                  "  pm.expect(String(vacancy.id)).to.eql(pm.collectionVariables.get('vacancyId'));",
                  "  pm.expect(vacancy.title).to.eql('Postman API Test Internship Updated');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "PUT",
            "header": [],
            "body": {
              "mode": "formdata",
              "formdata": [
                {
                  "key": "title",
                  "value": "Postman API Test Internship Updated",
                  "type": "text"
                },
                {
                  "key": "description",
                  "value": "Updated by the Postman API contract collection.",
                  "type": "text"
                },
                {
                  "key": "location",
                  "value": "Port of Spain",
                  "type": "text"
                },
                {
                  "key": "field_of_study",
                  "value": "{{fieldOfStudy}}",
                  "type": "text"
                },
                {
                  "key": "status",
                  "value": "Published",
                  "type": "text"
                }
              ]
            },
            "url": "{{baseUrl}}/api/company/vacancies/{{vacancyId}}",
            "description": "Proposed JSON endpoint using multipart/form-data."
          }
        }
      ]
    },
    {
      "name": "Proposed API - Student internship and application",
      "description": "Run Login student before these requests. Select a PDF file in the application_document form-data rows. The upload must be a valid PDF no larger than 10 MB.",
      "item": [
        {
          "name": "Login student",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('logs in with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('sets student identity and auth cookie', function () {",
                  "  pm.expect(pm.response.json().user.role).to.eql('regular_user');",
                  "  pm.expect(pm.response.headers.get('Set-Cookie') || '').to.include('access_token=');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{studentUsername}}\",\n  \"password\": \"{{studentPassword}}\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/auth/login"
          }
        },
        {
          "name": "Browse published internships",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns published vacancy page and pagination', function () {",
                  "  const body = pm.response.json();",
                  "  pm.expect(body.items).to.be.an('array');",
                  "  pm.expect(body.pagination.current_page).to.eql(Number(pm.collectionVariables.get('page')));",
                  "  body.items.forEach(function (item) { pm.expect(item.status).to.eql('Published'); });",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/internships?q={{searchQuery}}&field_of_study={{fieldOfStudy}}&page={{page}}",
            "description": "Proposed JSON endpoint. Student authentication required."
          }
        },
        {
          "name": "View internship details",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns published vacancy details', function () {",
                  "  const vacancy = pm.response.json();",
                  "  pm.expect(String(vacancy.id)).to.eql(pm.collectionVariables.get('vacancyId'));",
                  "  pm.expect(vacancy.status).to.eql('Published');",
                  "  pm.expect(vacancy.is_published).to.eql(true);",
                  "  pm.expect(vacancy).to.have.property('already_applied');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/internships/{{vacancyId}}",
            "description": "Proposed JSON endpoint. Requires a published vacancy ID and student authentication."
          }
        },
        {
          "name": "Download vacancy document",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns a document content type', function () {",
                  "  pm.expect(pm.response.headers.get('Content-Type') || '').not.to.eql('application/json');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/internships/{{vacancyId}}/documents/{{vacancyDocumentId}}",
            "description": "Proposed JSON endpoint. Optional fixture test: set vacancyDocumentId to a supplementary document linked to this published vacancy."
          }
        },
        {
          "name": "Apply to internship",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('creates application with HTTP 201', function () { pm.response.to.have.status(201); });",
                  "pm.test('returns submitted application and PDF metadata', function () {",
                  "  const application = pm.response.json();",
                  "  pm.expect(String(application.vacancy_id)).to.eql(pm.collectionVariables.get('vacancyId'));",
                  "  pm.expect(application.status).to.eql('Submitted');",
                  "  pm.expect(application.documents).to.be.an('array').that.is.not.empty;",
                  "  pm.expect(application.documents[0].type).to.eql('application/pdf');",
                  "  pm.collectionVariables.set('applicationId', String(application.id));",
                  "  pm.collectionVariables.set('documentId', String(application.documents[0].id));",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "formdata",
              "formdata": [
                {
                  "key": "application_document",
                  "type": "file",
                  "src": ""
                }
              ]
            },
            "url": "{{baseUrl}}/api/internships/{{vacancyId}}/applications",
            "description": "Proposed JSON endpoint. Select a valid PDF in the application_document field before sending."
          }
        },
        {
          "name": "List my applications",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns the created application in a paginated list', function () {",
                  "  const body = pm.response.json();",
                  "  pm.expect(body.items).to.be.an('array');",
                  "  pm.expect(body.pagination).to.have.property('total_count');",
                  "  pm.expect(body.items.some(function (item) { return String(item.id) === pm.collectionVariables.get('applicationId'); })).to.eql(true);",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/student/applications?page={{page}}",
            "description": "Proposed JSON endpoint. Requires student authentication."
          }
        },
        {
          "name": "Replace application document",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('replaces document with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('confirms document replacement', function () {",
                  "  pm.expect(pm.response.json().message).to.eql('application document updated');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "PUT",
            "header": [],
            "body": {
              "mode": "formdata",
              "formdata": [
                {
                  "key": "application_document",
                  "type": "file",
                  "src": ""
                }
              ]
            },
            "url": "{{baseUrl}}/api/student/applications/{{applicationId}}/document",
            "description": "Proposed JSON endpoint. Select another valid PDF. Application must still be in Submitted status."
          }
        }
      ]
    },
    {
      "name": "Proposed API - Company application review",
      "description": "Run Login company before this folder. The company account must own the vacancy referenced by vacancyId.",
      "item": [
        {
          "name": "Login company",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('logs in with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('authenticates company account', function () {",
                  "  pm.expect(pm.response.json().user.role).to.eql('company');",
                  "  pm.expect(pm.response.headers.get('Set-Cookie') || '').to.include('access_token=');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{companyUsername}}\",\n  \"password\": \"{{companyPassword}}\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/auth/login"
          }
        },
        {
          "name": "Browse applications for vacancy",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns application results and pagination', function () {",
                  "  const body = pm.response.json();",
                  "  pm.expect(body.items).to.be.an('array');",
                  "  pm.expect(body.pagination).to.have.property('total_count');",
                  "  body.items.forEach(function (item) { pm.expect(item.vacancy_id).to.eql(Number(pm.collectionVariables.get('vacancyId'))); });",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/company/vacancies/{{vacancyId}}/applications?q={{searchQuery}}&education_level={{educationLevel}}&status_sort=Shortlisted&page={{page}}",
            "description": "Proposed JSON endpoint. Company must own the vacancy."
          }
        },
        {
          "name": "Review application",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns matching vacancy and application', function () {",
                  "  const body = pm.response.json();",
                  "  pm.expect(String(body.application.id)).to.eql(pm.collectionVariables.get('applicationId'));",
                  "  pm.expect(String(body.application.vacancy_id)).to.eql(pm.collectionVariables.get('vacancyId'));",
                  "  pm.expect(body.application.student).to.be.an('object');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/company/vacancies/{{vacancyId}}/applications/{{applicationId}}",
            "description": "Proposed JSON endpoint. Company must own the vacancy."
          }
        },
        {
          "name": "Shortlist application",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('updates application with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns Shortlisted status', function () {",
                  "  const application = pm.response.json();",
                  "  pm.expect(application.status).to.eql('Shortlisted');",
                  "  pm.collectionVariables.set('applicationStatus', application.status);",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "PUT",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"status\": \"Shortlisted\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/company/vacancies/{{vacancyId}}/applications/{{applicationId}}",
            "description": "Proposed JSON endpoint."
          }
        },
        {
          "name": "Reject application",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('updates application with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns Rejected status', function () { pm.expect(pm.response.json().status).to.eql('Rejected'); });"
                ]
              }
            }
          ],
          "request": {
            "method": "PUT",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"status\": \"Rejected\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/company/vacancies/{{vacancyId}}/applications/{{applicationId}}",
            "description": "Proposed JSON endpoint. Optional alternative to Shortlist application; running both applies Reject last."
          }
        },
        {
          "name": "Finish application review",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('finishes review with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('returns updated application count', function () {",
                  "  pm.expect(pm.response.json().updated_count).to.be.a('number');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [],
            "url": "{{baseUrl}}/api/company/vacancies/{{vacancyId}}/applications/finish-review",
            "description": "Proposed JSON endpoint. Changes applications currently Under Review."
          }
        }
      ]
    },
    {
      "name": "Proposed API - Student withdrawal and sign out",
      "description": "Run Login student before this folder. Withdrawal deletes the application and its association, so run this after company review tests.",
      "item": [
        {
          "name": "Login student",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('logs in with HTTP 200', function () { pm.response.to.have.status(200); });",
                  "pm.test('authenticates student account', function () { pm.expect(pm.response.json().user.role).to.eql('regular_user'); });"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"{{studentUsername}}\",\n  \"password\": \"{{studentPassword}}\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": "{{baseUrl}}/api/auth/login"
          }
        },
        {
          "name": "Withdraw application",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('withdraws application with HTTP 204', function () { pm.response.to.have.status(204); });",
                  "pm.test('returns no response body', function () { pm.expect(pm.response.text()).to.eql(''); });"
                ]
              }
            }
          ],
          "request": {
            "method": "DELETE",
            "header": [],
            "url": "{{baseUrl}}/api/student/applications/{{applicationId}}",
            "description": "Proposed JSON endpoint. The application must belong to the signed-in student."
          }
        },
        {
          "name": "Sign out",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('signs out with HTTP 204', function () { pm.response.to.have.status(204); });",
                  "pm.test('clears the access token cookie', function () {",
                  "  pm.expect(pm.response.headers.get('Set-Cookie') || '').to.match(/access_token=.*(Max-Age=0|expires=Thu, 01 Jan 1970)/i);",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [],
            "url": "{{baseUrl}}/api/auth/logout",
            "description": "Implemented JSON endpoint. Requires authentication and clears the access_token cookie."
          }
        },
        {
          "name": "Current user rejects unauthenticated request",
          "event": [
            {
              "listen": "test",
              "script": {
                "type": "text/javascript",
                "exec": [
                  "pm.test('returns HTTP 401', function () { pm.response.to.have.status(401); });",
                  "pm.test('returns authentication error', function () {",
                  "  pm.expect(pm.response.json().detail).to.eql('Could not validate credentials');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "header": [],
            "url": "{{baseUrl}}/api/me",
            "description": "Implemented JSON endpoint. Run after Sign out; confirms the cleared cookie is no longer accepted."
          }
        }
      ]
    }
  ]
}
