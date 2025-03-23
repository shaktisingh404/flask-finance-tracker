def validation_error_response(error):
    # Handle both ValidationError objects and direct dictionaries
    if hasattr(error, "messages"):
        # Case when error is a ValidationError object
        if isinstance(error.messages, dict):
            formatted_errors = {
                field: messages[0] if isinstance(messages, list) else messages
                for field, messages in error.messages.items()
            }
        elif isinstance(error.messages, list):
            formatted_errors = error.messages[0] if len(error.messages) > 0 else "error"
        else:
            formatted_errors = str(error.messages)
    else:
        # Case when error is already a dictionary or string
        if isinstance(error, dict):
            formatted_errors = error
        else:
            formatted_errors = str(error)

    return {"error": formatted_errors}, 400
