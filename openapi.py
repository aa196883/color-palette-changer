"""OpenAPI description for the local HTTP API."""

from __future__ import annotations


def openapi_document() -> dict:
    """Return the API contract as an OpenAPI 3.0 document."""
    error = {
        "type": "object",
        "required": ["error"],
        "properties": {"error": {"type": "string"}},
    }
    palette = {
        "type": "object",
        "required": ["colors", "seed", "color_space", "step_values", "palette_size"],
        "properties": {
            "colors": {"type": "array", "items": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}},
            "seed": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
            "color_space": {"type": "string", "example": "OKlab"},
            "step_values": {
                "type": "object",
                "required": ["lightness", "a", "b"],
                "properties": {
                    "lightness": {"type": "number"},
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
            },
            "palette_size": {"type": "integer", "minimum": 1, "maximum": 256},
        },
    }
    palette_record = {
        "type": "object",
        "required": ["id", "colors", "palette_size", "saved", "url"],
        "properties": {
            "id": {"type": "string"},
            "colors": palette["properties"]["colors"],
            "palette_size": palette["properties"]["palette_size"],
            "saved": {"type": "boolean"},
            "url": {"type": "string", "format": "uri-reference"},
        },
    }
    image_record = {
        "type": "object",
        "required": ["id", "name", "saved", "url"],
        "properties": {
            "id": {"type": "string", "example": "inputs:lenna.png"},
            "name": {"type": "string"},
            "saved": {"type": "boolean"},
            "url": {"type": "string", "format": "uri-reference"},
        },
    }
    json_response = {"application/json": {"schema": {"$ref": "#/components/schemas/Palette"}}}
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Color Palette Changer API",
            "version": "1.0.0",
            "description": "Generate palettes, manage local image resources, and recolor images.",
        },
        "servers": [{"url": "/"}],
        "paths": {
            "/api/palettes": {
                "get": {
                    "summary": "List saved palettes",
                    "responses": {
                        "200": {"description": "Palette library", "content": {"application/json": {"schema": {"type": "object", "properties": {"palettes": {"type": "array", "items": {"$ref": "#/components/schemas/PaletteRecord"}}}, "required": ["palettes"]}}}},
                    },
                },
                "post": {
                    "summary": "Generate a palette draft",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PaletteGenerationRequest"}}}},
                    "responses": {
                        "201": {"description": "Generated palette JSON", "headers": {"Location": {"schema": {"type": "string"}}, "X-Palette-ID": {"schema": {"type": "string"}}}, "content": json_response},
                        "400": {"$ref": "#/components/responses/BadRequest"},
                    },
                },
            },
            "/api/palettes/{id}": {
                "parameters": [{"$ref": "#/components/parameters/PaletteId"}],
                "get": {
                    "summary": "Get a palette JSON document",
                    "parameters": [{"$ref": "#/components/parameters/Download"}],
                    "responses": {"200": {"description": "Palette JSON", "content": json_response}, "404": {"$ref": "#/components/responses/NotFound"}},
                },
            },
            "/api/palettes/{id}/save": {
                "parameters": [{"$ref": "#/components/parameters/PaletteId"}],
                "post": {
                    "summary": "Save a palette draft to the library",
                    "responses": {"200": {"description": "Saved palette", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PaletteRecord"}}}}, "404": {"$ref": "#/components/responses/NotFound"}},
                },
            },
            "/api/images": {
                "get": {
                    "summary": "List eligible inputs and saved outputs",
                    "responses": {"200": {"description": "Image library", "content": {"application/json": {"schema": {"type": "object", "properties": {"images": {"type": "array", "items": {"$ref": "#/components/schemas/ImageRecord"}}}, "required": ["images"]}}}}},
                },
                "post": {
                    "summary": "Upload an image into inputs",
                    "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object", "required": ["image"], "properties": {"image": {"type": "string", "format": "binary"}}}}}},
                    "responses": {"201": {"description": "Uploaded image", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ImageRecord"}}}}, "400": {"$ref": "#/components/responses/BadRequest"}},
                },
            },
            "/api/images/{id}": {
                "parameters": [{"$ref": "#/components/parameters/ImageId"}],
                "get": {
                    "summary": "Get image bytes",
                    "parameters": [{"$ref": "#/components/parameters/Download"}],
                    "responses": {"200": {"description": "Image file", "content": {"image/*": {"schema": {"type": "string", "format": "binary"}}}}, "404": {"$ref": "#/components/responses/NotFound"}},
                },
            },
            "/api/mappings": {
                "post": {
                    "summary": "Create a recolored image draft",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MappingRequest"}}}},
                    "responses": {"201": {"description": "Mapped image draft", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ImageRecord"}}}}, "400": {"$ref": "#/components/responses/BadRequest"}, "404": {"$ref": "#/components/responses/NotFound"}},
                },
            },
            "/api/images/{id}/save": {
                "parameters": [{"$ref": "#/components/parameters/ImageId"}],
                "post": {
                    "summary": "Save a mapped image draft to outputs",
                    "responses": {"200": {"description": "Saved image", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ImageRecord"}}}}, "404": {"$ref": "#/components/responses/NotFound"}},
                },
            },
        },
        "components": {
            "parameters": {
                "PaletteId": {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                "ImageId": {"name": "id", "in": "path", "required": True, "schema": {"type": "string", "example": "inputs:lenna.png"}},
                "Download": {"name": "download", "in": "query", "required": False, "schema": {"type": "string", "enum": ["1"]}},
            },
            "schemas": {
                "Palette": palette,
                "PaletteRecord": palette_record,
                "ImageRecord": image_record,
                "PaletteGenerationRequest": {"type": "object", "properties": {"mode": {"type": "string", "enum": ["analogous", "complementary"], "default": "analogous"}, "seed": {"type": "string", "nullable": True}, "palette_size": {"type": "integer", "minimum": 1, "maximum": 256, "default": 5}, "lightness_step": {"type": "number", "minimum": -1, "maximum": 1}, "green_red_step": {"type": "number", "minimum": -1, "maximum": 1}, "blue_yellow_step": {"type": "number", "minimum": -1, "maximum": 1}}},
                "MappingRequest": {"type": "object", "required": ["palette_id", "image_id"], "properties": {"palette_id": {"type": "string"}, "image_id": {"type": "string", "example": "inputs:lenna.png"}, "image_mapping": {"type": "string", "enum": ["grayscaled", "oklab-clusters"], "default": "grayscaled"}}},
                "Error": error,
            },
            "responses": {
                "BadRequest": {"description": "Invalid request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                "NotFound": {"description": "Resource not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
            },
        },
    }
