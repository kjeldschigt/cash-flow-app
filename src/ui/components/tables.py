"""
Interactive Table Components for Cash Flow Dashboard
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
import io
import base64

class BaseTable:
    """Base table component with common functionality"""
    
    @staticmethod
    def _prepare_dataframe(df: pd.DataFrame, formatters: Dict[str, Callable] = None) -> pd.DataFrame:
        """Prepare DataFrame for display with formatting"""
        if df.empty:
            return df
        
        display_df = df.copy()
        
        # Apply custom formatters
        if formatters:
            for column, formatter in formatters.items():
                if column in display_df.columns:
                    display_df[column] = display_df[column].apply(formatter)
        
        return display_df
    
    @staticmethod
    def _add_export_functionality(df: pd.DataFrame, filename: str = "data"):
        """Add export buttons for CSV and Excel"""
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            # CSV Export
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">📄 Download CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            # Excel Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
            
            excel_data = buffer.getvalue()
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}.xlsx">📊 Download Excel</a>'
            st.markdown(href, unsafe_allow_html=True)

class TransactionTable:
    """Advanced transaction table with sorting, filtering, and pagination"""
    
    @staticmethod
    def render(
        data: pd.DataFrame,
        title: str = "Transactions",
        page_size: int = 20,
        show_filters: bool = True,
        show_search: bool = True,
        editable_columns: List[str] = None,
        formatters: Dict[str, Callable] = None,
        export_filename: str = "transactions"
    ):
        """
        Render interactive transaction table
        
        Args:
            data: Transaction DataFrame
            title: Table title
            page_size: Number of rows per page
            show_filters: Show column filters
            show_search: Show search functionality
            editable_columns: List of columns that can be edited
            formatters: Dictionary of column formatters
            export_filename: Filename for exports
        """
        if data.empty:
            st.warning("No transaction data available")
            return data
        
        st.subheader(title)
        
        # Initialize session state for filters
        if 'table_filters' not in st.session_state:
            st.session_state.table_filters = {}
        
        # Search functionality
        filtered_data = data.copy()
        
        if show_search:
            search_term = st.text_input("🔍 Search transactions", key=f"search_{title}")
            if search_term:
                # Search across all string columns
                string_columns = filtered_data.select_dtypes(include=['object']).columns
                mask = pd.Series([False] * len(filtered_data))
                
                for col in string_columns:
                    mask |= filtered_data[col].astype(str).str.contains(search_term, case=False, na=False)
                
                filtered_data = filtered_data[mask]
        
        # Column filters
        if show_filters and not filtered_data.empty:
            with st.expander("🎛️ Advanced Filters"):
                filter_cols = st.columns(min(len(filtered_data.columns), 4))
                
                for i, column in enumerate(filtered_data.columns):
                    col_idx = i % len(filter_cols)
                    
                    with filter_cols[col_idx]:
                        if filtered_data[column].dtype in ['object', 'category']:
                            # Categorical filter
                            unique_values = ['All'] + sorted(filtered_data[column].dropna().unique().tolist())
                            selected = st.selectbox(
                                f"Filter {column}",
                                unique_values,
                                key=f"filter_{column}_{title}"
                            )
                            
                            if selected != 'All':
                                filtered_data = filtered_data[filtered_data[column] == selected]
                        
                        elif pd.api.types.is_numeric_dtype(filtered_data[column]):
                            # Numeric range filter
                            min_val = float(filtered_data[column].min())
                            max_val = float(filtered_data[column].max())
                            
                            if min_val != max_val:
                                range_values = st.slider(
                                    f"{column} Range",
                                    min_val, max_val, (min_val, max_val),
                                    key=f"range_{column}_{title}"
                                )
                                filtered_data = filtered_data[
                                    (filtered_data[column] >= range_values[0]) & 
                                    (filtered_data[column] <= range_values[1])
                                ]
                        
                        elif pd.api.types.is_datetime64_any_dtype(filtered_data[column]):
                            # Date range filter
                            min_date = filtered_data[column].min().date()
                            max_date = filtered_data[column].max().date()
                            
                            date_range = st.date_input(
                                f"{column} Range",
                                value=(min_date, max_date),
                                min_value=min_date,
                                max_value=max_date,
                                key=f"date_{column}_{title}"
                            )
                            
                            if len(date_range) == 2:
                                start_date, end_date = date_range
                                filtered_data = filtered_data[
                                    (filtered_data[column].dt.date >= start_date) & 
                                    (filtered_data[column].dt.date <= end_date)
                                ]
        
        # Pagination
        total_rows = len(filtered_data)
        total_pages = (total_rows - 1) // page_size + 1 if total_rows > 0 else 1
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                st.write(f"Total: {total_rows} rows")
            
            with col2:
                page = st.selectbox(
                    "Page",
                    range(1, total_pages + 1),
                    key=f"page_{title}"
                )
            
            with col3:
                st.write(f"Page {page} of {total_pages}")
            
            # Get page data
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_data = filtered_data.iloc[start_idx:end_idx]
        else:
            page_data = filtered_data
        
        # Apply formatters
        display_data = BaseTable._prepare_dataframe(page_data, formatters)
        
        # Display table
        if editable_columns:
            # Editable table using data_editor
            edited_data = st.data_editor(
                display_data,
                column_config={
                    col: st.column_config.TextColumn(col) for col in editable_columns
                },
                use_container_width=True,
                key=f"editor_{title}"
            )
            
            # Return edited data mapped back to original indices
            if not edited_data.equals(display_data):
                # Handle edits here - would need callback mechanism
                st.success("Changes detected! Implement save functionality.")
            
            result_data = edited_data
        else:
            # Read-only table
            st.dataframe(display_data, use_container_width=True)
            result_data = page_data
        
        # Export functionality
        BaseTable._add_export_functionality(filtered_data, export_filename)
        
        # Summary statistics
        with st.expander("📊 Summary Statistics"):
            numeric_cols = filtered_data.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary_stats = filtered_data[numeric_cols].describe()
                st.dataframe(summary_stats, use_container_width=True)
        
        return result_data

class CostBreakdownTable:
    """Cost breakdown table with drill-down capability"""
    
    @staticmethod
    def render(
        data: pd.DataFrame,
        category_column: str = "category",
        amount_column: str = "amount",
        date_column: str = "date",
        title: str = "Cost Breakdown",
        show_subcategories: bool = True,
        export_filename: str = "cost_breakdown"
    ):
        """
        Render cost breakdown table with drill-down
        
        Args:
            data: Cost data DataFrame
            category_column: Name of category column
            amount_column: Name of amount column
            date_column: Name of date column
            title: Table title
            show_subcategories: Enable subcategory drill-down
            export_filename: Filename for exports
        """
        if data.empty:
            st.warning("No cost data available")
            return
        
        st.subheader(title)
        
        # Calculate category totals
        category_totals = data.groupby(category_column)[amount_column].agg(['sum', 'count', 'mean']).reset_index()
        category_totals.columns = ['Category', 'Total Amount', 'Transaction Count', 'Average Amount']
        
        # Format currency columns
        formatters = {
            'Total Amount': lambda x: f"${x:,.2f}",
            'Average Amount': lambda x: f"${x:,.2f}"
        }
        
        display_totals = BaseTable._prepare_dataframe(category_totals, formatters)
        
        # Display category summary
        st.write("### Category Summary")
        st.dataframe(display_totals, use_container_width=True)
        
        # Drill-down functionality
        if show_subcategories:
            st.write("### Detailed Breakdown")
            
            selected_category = st.selectbox(
                "Select category for detailed view:",
                ['All Categories'] + sorted(data[category_column].unique().tolist()),
                key=f"category_select_{title}"
            )
            
            if selected_category != 'All Categories':
                category_data = data[data[category_column] == selected_category].copy()
                
                # Show detailed transactions for selected category
                st.write(f"#### {selected_category} - Detailed Transactions")
                
                # Add subcategory analysis if there are subcategory patterns
                if 'subcategory' in category_data.columns:
                    subcategory_totals = category_data.groupby('subcategory')[amount_column].agg(['sum', 'count']).reset_index()
                    subcategory_totals.columns = ['Subcategory', 'Total Amount', 'Count']
                    subcategory_totals['Total Amount'] = subcategory_totals['Total Amount'].apply(lambda x: f"${x:,.2f}")
                    
                    st.write("##### Subcategory Breakdown")
                    st.dataframe(subcategory_totals, use_container_width=True)
                
                # Show individual transactions
                transaction_formatters = {
                    amount_column: lambda x: f"${x:,.2f}",
                    date_column: lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else ''
                }
                
                TransactionTable.render(
                    category_data,
                    title=f"{selected_category} Transactions",
                    formatters=transaction_formatters,
                    export_filename=f"{export_filename}_{selected_category.lower().replace(' ', '_')}"
                )
        
        # Export functionality for summary
        BaseTable._add_export_functionality(category_totals, f"{export_filename}_summary")

class ForecastTable:
    """Forecast table with editable scenarios"""
    
    @staticmethod
    def render(
        base_forecast: pd.DataFrame,
        title: str = "Financial Forecast",
        editable_scenarios: bool = True,
        scenario_columns: List[str] = None,
        export_filename: str = "forecast"
    ):
        """
        Render forecast table with scenario editing
        
        Args:
            base_forecast: Base forecast DataFrame
            title: Table title
            editable_scenarios: Allow scenario editing
            scenario_columns: List of scenario column names
            export_filename: Filename for exports
        """
        if base_forecast.empty:
            st.warning("No forecast data available")
            return base_forecast
        
        st.subheader(title)
        
        # Initialize scenarios in session state
        if 'forecast_scenarios' not in st.session_state:
            st.session_state.forecast_scenarios = {}
        
        forecast_data = base_forecast.copy()
        
        # Scenario management
        if editable_scenarios:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                scenario_name = st.text_input("Scenario Name", value="Custom Scenario")
            
            with col2:
                if st.button("Create Scenario"):
                    if scenario_name and scenario_name not in st.session_state.forecast_scenarios:
                        st.session_state.forecast_scenarios[scenario_name] = forecast_data.copy()
                        st.success(f"Scenario '{scenario_name}' created!")
            
            with col3:
                if st.session_state.forecast_scenarios:
                    scenario_to_delete = st.selectbox("Delete Scenario", 
                                                    [''] + list(st.session_state.forecast_scenarios.keys()))
                    if scenario_to_delete and st.button("Delete"):
                        del st.session_state.forecast_scenarios[scenario_to_delete]
                        st.success(f"Scenario '{scenario_to_delete}' deleted!")
                        st.rerun()
        
        # Display scenarios tabs
        if st.session_state.forecast_scenarios:
            scenario_tabs = st.tabs(['Base Forecast'] + list(st.session_state.forecast_scenarios.keys()))
            
            # Base forecast tab
            with scenario_tabs[0]:
                st.dataframe(forecast_data, use_container_width=True)
            
            # Scenario tabs
            for i, (scenario_name, scenario_data) in enumerate(st.session_state.forecast_scenarios.items()):
                with scenario_tabs[i + 1]:
                    if editable_scenarios:
                        # Editable scenario
                        edited_scenario = st.data_editor(
                            scenario_data,
                            use_container_width=True,
                            key=f"scenario_editor_{scenario_name}"
                        )
                        
                        # Update scenario data
                        st.session_state.forecast_scenarios[scenario_name] = edited_scenario
                        
                        # Show scenario comparison
                        if not edited_scenario.equals(forecast_data):
                            st.write("#### Variance from Base Forecast")
                            
                            numeric_cols = edited_scenario.select_dtypes(include=['number']).columns
                            variance_data = {}
                            
                            for col in numeric_cols:
                                if col in forecast_data.columns:
                                    variance = edited_scenario[col] - forecast_data[col]
                                    variance_pct = (variance / forecast_data[col] * 100).fillna(0)
                                    variance_data[f"{col}_variance"] = variance
                                    variance_data[f"{col}_variance_pct"] = variance_pct
                            
                            if variance_data:
                                variance_df = pd.DataFrame(variance_data)
                                st.dataframe(variance_df, use_container_width=True)
                    else:
                        st.dataframe(scenario_data, use_container_width=True)
        else:
            # No scenarios, just show base forecast
            if editable_scenarios:
                edited_forecast = st.data_editor(
                    forecast_data,
                    use_container_width=True,
                    key=f"base_forecast_editor"
                )
                forecast_data = edited_forecast
            else:
                st.dataframe(forecast_data, use_container_width=True)
        
        # Forecast summary metrics
        with st.expander("📊 Forecast Summary"):
            numeric_cols = forecast_data.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) > 0:
                col1, col2, col3, col4 = st.columns(4)
                
                for i, col in enumerate(numeric_cols[:4]):
                    with [col1, col2, col3, col4][i]:
                        total = forecast_data[col].sum()
                        avg = forecast_data[col].mean()
                        
                        st.metric(
                            f"Total {col}",
                            f"${total:,.2f}" if 'amount' in col.lower() or 'revenue' in col.lower() else f"{total:,.2f}"
                        )
                        st.metric(
                            f"Avg {col}",
                            f"${avg:,.2f}" if 'amount' in col.lower() or 'revenue' in col.lower() else f"{avg:,.2f}"
                        )
        
        # Export functionality
        BaseTable._add_export_functionality(forecast_data, export_filename)
        
        # Export all scenarios
        if st.session_state.forecast_scenarios:
            if st.button("📊 Export All Scenarios"):
                # Create multi-sheet Excel file
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    forecast_data.to_excel(writer, sheet_name='Base_Forecast', index=False)
                    
                    for scenario_name, scenario_data in st.session_state.forecast_scenarios.items():
                        safe_name = scenario_name.replace(' ', '_')[:30]  # Excel sheet name limit
                        scenario_data.to_excel(writer, sheet_name=safe_name, index=False)
                
                excel_data = buffer.getvalue()
                b64 = base64.b64encode(excel_data).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="all_scenarios.xlsx">📊 Download All Scenarios</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        return forecast_data

class PivotTable:
    """Interactive pivot table component"""
    
    @staticmethod
    def render(
        data: pd.DataFrame,
        title: str = "Pivot Analysis",
        default_index: List[str] = None,
        default_columns: List[str] = None,
        default_values: List[str] = None,
        export_filename: str = "pivot_analysis"
    ):
        """
        Render interactive pivot table
        
        Args:
            data: Source DataFrame
            title: Table title
            default_index: Default index columns
            default_columns: Default column fields
            default_values: Default value fields
            export_filename: Filename for exports
        """
        if data.empty:
            st.warning("No data available for pivot analysis")
            return
        
        st.subheader(title)
        
        # Pivot configuration
        col1, col2, col3 = st.columns(3)
        
        available_columns = data.columns.tolist()
        
        with col1:
            index_cols = st.multiselect(
                "Index (Rows)",
                available_columns,
                default=default_index or [],
                key=f"pivot_index_{title}"
            )
        
        with col2:
            column_cols = st.multiselect(
                "Columns",
                available_columns,
                default=default_columns or [],
                key=f"pivot_columns_{title}"
            )
        
        with col3:
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            value_cols = st.multiselect(
                "Values",
                numeric_cols,
                default=default_values or numeric_cols[:1] if numeric_cols else [],
                key=f"pivot_values_{title}"
            )
        
        # Aggregation function
        agg_func = st.selectbox(
            "Aggregation Function",
            ['sum', 'mean', 'count', 'min', 'max', 'std'],
            key=f"pivot_agg_{title}"
        )
        
        # Create pivot table
        if index_cols and value_cols:
            try:
                pivot_data = pd.pivot_table(
                    data,
                    index=index_cols,
                    columns=column_cols if column_cols else None,
                    values=value_cols,
                    aggfunc=agg_func,
                    fill_value=0
                )
                
                # Display pivot table
                st.dataframe(pivot_data, use_container_width=True)
                
                # Export functionality
                BaseTable._add_export_functionality(pivot_data.reset_index(), export_filename)
                
                return pivot_data
                
            except Exception as e:
                st.error(f"Error creating pivot table: {str(e)}")
        else:
            st.info("Please select at least one index column and one value column to create the pivot table.")

# Convenience functions for common table patterns
def render_financial_summary_table(data: Dict[str, pd.DataFrame], title: str = "Financial Summary"):
    """Render financial summary table with multiple data sources"""
    st.subheader(title)
    
    summary_data = []
    
    for category, df in data.items():
        if not df.empty and 'amount' in df.columns:
            total = df['amount'].sum()
            count = len(df)
            avg = df['amount'].mean()
            
            summary_data.append({
                'Category': category,
                'Total Amount': f"${total:,.2f}",
                'Transaction Count': count,
                'Average Amount': f"${avg:,.2f}"
            })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
        
        BaseTable._add_export_functionality(summary_df, "financial_summary")

def render_comparison_table(data1: pd.DataFrame, data2: pd.DataFrame, 
                          labels: List[str] = ['Current', 'Previous'],
                          title: str = "Period Comparison"):
    """Render side-by-side comparison table"""
    st.subheader(title)
    
    if data1.empty or data2.empty:
        st.warning("Insufficient data for comparison")
        return
    
    # Align data for comparison
    numeric_cols = data1.select_dtypes(include=['number']).columns
    
    comparison_data = {}
    
    for col in numeric_cols:
        if col in data2.columns:
            comparison_data[f"{labels[0]} {col}"] = data1[col].sum()
            comparison_data[f"{labels[1]} {col}"] = data2[col].sum()
            
            # Calculate variance
            variance = data1[col].sum() - data2[col].sum()
            variance_pct = (variance / data2[col].sum() * 100) if data2[col].sum() != 0 else 0
            
            comparison_data[f"{col} Variance"] = f"${variance:,.2f}" if 'amount' in col.lower() else f"{variance:,.2f}"
            comparison_data[f"{col} Variance %"] = f"{variance_pct:.1f}%"
    
    if comparison_data:
        comparison_df = pd.DataFrame([comparison_data])
        st.dataframe(comparison_df, use_container_width=True)
        
        BaseTable._add_export_functionality(comparison_df, "period_comparison")
