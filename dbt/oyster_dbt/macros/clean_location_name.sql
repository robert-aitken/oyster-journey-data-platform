{% macro clean_location_name(location_text) %}
trim(
    regexp_replace(
        regexp_replace(
            {{ location_text }},
            '\s*\[[^\]]*\]\s*',
            ' ',
            'g'
        ),
        '\s*\([^\)]*\)\s*',
        ' ',
        'g'
    )
)
{% endmacro %}
