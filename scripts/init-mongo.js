// MongoDB initialization script for MindMitra
// This script runs when the MongoDB container starts for the first time

// Switch to the mindmitra database
db = db.getSiblingDB('mindmitra');

// Create collections with validation
db.createCollection("users", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["id", "email", "name", "role", "hashed_password", "created_at", "updated_at"],
            properties: {
                id: { bsonType: "string" },
                email: { bsonType: "string" },
                name: { bsonType: "string" },
                role: { enum: ["user", "admin", "therapist"] },
                hashed_password: { bsonType: "string" },
                emergency_contacts: { bsonType: "array" },
                is_active: { bsonType: "bool" },
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" }
            }
        }
    }
});

db.createCollection("journal_entries", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["id", "user_id", "content", "created_at", "updated_at"],
            properties: {
                id: { bsonType: "string" },
                user_id: { bsonType: "string" },
                content: { bsonType: "string" },
                mood_score: { bsonType: "double" },
                emotion_labels: { bsonType: "array" },
                tags: { bsonType: "array" },
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" }
            }
        }
    }
});

db.createCollection("sos_alerts", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["id", "user_id", "trigger_type", "severity", "status", "created_at", "updated_at"],
            properties: {
                id: { bsonType: "string" },
                user_id: { bsonType: "string" },
                trigger_type: { enum: ["automatic", "manual"] },
                severity: { enum: ["low", "medium", "high", "critical"] },
                reason: { bsonType: "string" },
                emotion_data: { bsonType: "object" },
                status: { enum: ["pending", "sent", "cancelled", "acknowledged"] },
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" },
                sent_at: { bsonType: "date" },
                acknowledged_at: { bsonType: "date" }
            }
        }
    }
});

db.createCollection("chat_history", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["id", "user_id", "content", "is_user", "created_at"],
            properties: {
                id: { bsonType: "string" },
                user_id: { bsonType: "string" },
                content: { bsonType: "string" },
                message_type: { bsonType: "string" },
                is_user: { bsonType: "bool" },
                emotion_data: { bsonType: "object" },
                created_at: { bsonType: "date" }
            }
        }
    }
});

db.createCollection("emergency_contacts", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["id", "user_id", "name", "phone", "relationship"],
            properties: {
                id: { bsonType: "string" },
                user_id: { bsonType: "string" },
                name: { bsonType: "string" },
                phone: { bsonType: "string" },
                email: { bsonType: "string" },
                relationship: { bsonType: "string" },
                created_at: { bsonType: "date" }
            }
        }
    }
});

// Create indexes for better performance
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "created_at": 1 });

db.journal_entries.createIndex({ "user_id": 1 });
db.journal_entries.createIndex({ "user_id": 1, "created_at": -1 });
db.journal_entries.createIndex({ "created_at": 1 });

db.sos_alerts.createIndex({ "user_id": 1 });
db.sos_alerts.createIndex({ "user_id": 1, "created_at": -1 });
db.sos_alerts.createIndex({ "status": 1 });

db.chat_history.createIndex({ "user_id": 1 });
db.chat_history.createIndex({ "user_id": 1, "created_at": -1 });

db.emergency_contacts.createIndex({ "user_id": 1 });

db.createCollection("password_reset_tokens");
db.password_reset_tokens.createIndex({ "token_hash": 1 }, { unique: true });
db.password_reset_tokens.createIndex({ "user_id": 1 });
db.password_reset_tokens.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });

print("MindMitra database initialized successfully!"); 