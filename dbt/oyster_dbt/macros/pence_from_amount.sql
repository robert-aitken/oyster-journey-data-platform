{% macro pence_from_amount(amount_text) %}
case
    when {{ amount_text }} is null then null
    else cast(round(try_cast({{ amount_text }} as decimal(18, 2)) * 100, 0) as bigint)
end
{% endmacro %}
