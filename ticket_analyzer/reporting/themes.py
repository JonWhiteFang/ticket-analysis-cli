"""Theme management and customization for HTML reports.

This module provides comprehensive theming capabilities for HTML reports including
color schemes, layout options, branding integration, and configuration management.
Supports light/dark themes with automatic detection and custom theme creation.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum

from ..models.exceptions import ReportGenerationError

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """Available theme types."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"


class ColorScheme(Enum):
    """Predefined color schemes."""
    DEFAULT = "default"
    CORPORATE = "corporate"
    MODERN = "modern"
    MINIMAL = "minimal"
    HIGH_CONTRAST = "high_contrast"
    AMAZON = "amazon"


@dataclass
class ColorPalette:
    """Color palette configuration for themes.
    
    Attributes:
        primary: Primary brand color
        secondary: Secondary accent color
        accent: Accent color for highlights
        success: Success state color
        warning: Warning state color
        error: Error state color
        background: Main background color
        surface: Surface/card background color
        text: Primary text color
        text_muted: Muted/secondary text color
        border: Border color
    """
    primary: str = "#2c3e50"
    secondary: str = "#3498db"
    accent: str = "#e74c3c"
    success: str = "#27ae60"
    warning: str = "#f39c12"
    error: str = "#e74c3c"
    background: str = "#ffffff"
    surface: str = "#f8f9fa"
    text: str = "#2c3e50"
    text_muted: str = "#6c757d"
    border: str = "#dee2e6"
    
    def to_css_variables(self) -> str:
        """Convert color palette to CSS custom properties.
        
        Returns:
            CSS string with custom property definitions.
        """
        css_vars = []
        for key, value in asdict(self).items():
            css_key = key.replace('_', '-')
            css_vars.append(f"  --{css_key}-color: {value};")
        
        return "\n".join(css_vars)


@dataclass
class LayoutConfig:
    """Layout configuration for reports.
    
    Attributes:
        max_width: Maximum content width
        padding: Default padding
        border_radius: Default border radius
        shadow: Box shadow configuration
        font_family: Primary font family
        font_size_base: Base font size
        line_height: Base line height
        grid_gap: Grid gap for layouts
    """
    max_width: str = "1200px"
    padding: str = "20px"
    border_radius: str = "8px"
    shadow: str = "0 2px 4px rgba(0,0,0,0.1)"
    font_family: str = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    font_size_base: str = "16px"
    line_height: str = "1.6"
    grid_gap: str = "2rem"
    
    def to_css_variables(self) -> str:
        """Convert layout config to CSS custom properties.
        
        Returns:
            CSS string with custom property definitions.
        """
        css_vars = []
        for key, value in asdict(self).items():
            css_key = key.replace('_', '-')
            css_vars.append(f"  --{css_key}: {value};")
        
        return "\n".join(css_vars)


@dataclass
class BrandingConfig:
    """Branding configuration for reports.
    
    Attributes:
        logo_url: URL or path to logo image
        logo_width: Logo width
        logo_height: Logo height
        company_name: Company name for branding
        report_title_prefix: Prefix for report titles
        footer_text: Custom footer text
        show_logo: Whether to display logo
        show_company_name: Whether to display company name
    """
    logo_url: Optional[str] = None
    logo_width: str = "120px"
    logo_height: str = "auto"
    company_name: Optional[str] = None
    report_title_prefix: Optional[str] = None
    footer_text: Optional[str] = None
    show_logo: bool = False
    show_company_name: bool = False


@dataclass
class Theme:
    """Complete theme configuration.
    
    Attributes:
        name: Theme name
        type: Theme type (light, dark, auto, custom)
        color_scheme: Color scheme identifier
        colors: Color palette configuration
        layout: Layout configuration
        branding: Branding configuration
        custom_css: Additional custom CSS
        metadata: Theme metadata
    """
    name: str
    type: ThemeType = ThemeType.LIGHT
    color_scheme: ColorScheme = ColorScheme.DEFAULT
    colors: ColorPalette = field(default_factory=ColorPalette)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    branding: BrandingConfig = field(default_factory=BrandingConfig)
    custom_css: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_css(self) -> str:
        """Generate complete CSS for the theme.
        
        Returns:
            Complete CSS string for the theme.
        """
        css_parts = [
            ":root {",
            self.colors.to_css_variables(),
            self.layout.to_css_variables(),
            "}"
        ]
        
        # Add dark theme variant if applicable
        if self.type == ThemeType.DARK or self.type == ThemeType.AUTO:
            dark_colors = self._get_dark_colors()
            css_parts.extend([
                "",
                "[data-theme=\"dark\"] {",
                dark_colors.to_css_variables(),
                "}"
            ])
        
        # Add custom CSS
        if self.custom_css:
            css_parts.extend(["", "/* Custom CSS */", self.custom_css])
        
        return "\n".join(css_parts)
    
    def _get_dark_colors(self) -> ColorPalette:
        """Get dark theme color palette.
        
        Returns:
            ColorPalette configured for dark theme.
        """
        return ColorPalette(
            primary="#ecf0f1",
            secondary="#3498db",
            accent="#e74c3c",
            success="#27ae60",
            warning="#f39c12",
            error="#e74c3c",
            background="#2c3e50",
            surface="#34495e",
            text="#ecf0f1",
            text_muted="#bdc3c7",
            border="#4a5568"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary.
        
        Returns:
            Dictionary representation of the theme.
        """
        return {
            "name": self.name,
            "type": self.type.value,
            "color_scheme": self.color_scheme.value,
            "colors": asdict(self.colors),
            "layout": asdict(self.layout),
            "branding": asdict(self.branding),
            "custom_css": self.custom_css,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Theme:
        """Create theme from dictionary.
        
        Args:
            data: Dictionary containing theme data.
            
        Returns:
            Theme instance.
        """
        theme = cls(
            name=data["name"],
            type=ThemeType(data.get("type", "light")),
            color_scheme=ColorScheme(data.get("color_scheme", "default")),
            custom_css=data.get("custom_css", ""),
            metadata=data.get("metadata", {})
        )
        
        if "colors" in data:
            theme.colors = ColorPalette(**data["colors"])
        
        if "layout" in data:
            theme.layout = LayoutConfig(**data["layout"])
        
        if "branding" in data:
            theme.branding = BrandingConfig(**data["branding"])
        
        return theme


class ThemeManager:
    """Manager for theme operations and customization.
    
    Provides functionality for loading, saving, and managing themes including
    predefined themes, custom themes, and theme customization options.
    
    Attributes:
        themes_dir: Directory containing theme files
        current_theme: Currently active theme
        predefined_themes: Dictionary of predefined themes
    """
    
    def __init__(self, themes_dir: Optional[str] = None) -> None:
        """Initialize theme manager.
        
        Args:
            themes_dir: Directory for theme files. Defaults to 'themes' in project root.
        """
        self.themes_dir = self._setup_themes_directory(themes_dir)
        self.current_theme: Optional[Theme] = None
        self.predefined_themes = self._load_predefined_themes()
        
        logger.info(f"Theme manager initialized with directory: {self.themes_dir}")
    
    def get_theme(self, theme_name: str) -> Theme:
        """Get theme by name.
        
        Args:
            theme_name: Name of the theme to retrieve.
            
        Returns:
            Theme instance.
            
        Raises:
            ReportGenerationError: If theme not found.
        """
        # Check predefined themes first
        if theme_name in self.predefined_themes:
            return self.predefined_themes[theme_name]
        
        # Try to load from file
        theme_file = self.themes_dir / f"{theme_name}.json"
        if theme_file.exists():
            return self._load_theme_from_file(theme_file)
        
        # Fallback to default theme
        logger.warning(f"Theme '{theme_name}' not found, using default")
        return self.predefined_themes["default"]
    
    def save_theme(self, theme: Theme) -> None:
        """Save theme to file.
        
        Args:
            theme: Theme to save.
            
        Raises:
            ReportGenerationError: If saving fails.
        """
        try:
            theme_file = self.themes_dir / f"{theme.name}.json"
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme.to_dict(), f, indent=2)
            
            logger.info(f"Theme '{theme.name}' saved to {theme_file}")
            
        except Exception as e:
            raise ReportGenerationError(f"Failed to save theme '{theme.name}': {e}")
    
    def create_custom_theme(self, name: str, base_theme: str = "default",
                           customizations: Optional[Dict[str, Any]] = None) -> Theme:
        """Create custom theme based on existing theme.
        
        Args:
            name: Name for the new theme.
            base_theme: Base theme to customize.
            customizations: Dictionary of customizations to apply.
            
        Returns:
            New custom theme.
        """
        base = self.get_theme(base_theme)
        
        # Create copy of base theme
        custom_theme = Theme(
            name=name,
            type=base.type,
            color_scheme=ColorScheme.CUSTOM,
            colors=ColorPalette(**asdict(base.colors)),
            layout=LayoutConfig(**asdict(base.layout)),
            branding=BrandingConfig(**asdict(base.branding)),
            custom_css=base.custom_css,
            metadata={"base_theme": base_theme, "created_at": "now"}
        )
        
        # Apply customizations
        if customizations:
            self._apply_customizations(custom_theme, customizations)
        
        return custom_theme
    
    def list_themes(self) -> List[str]:
        """List available theme names.
        
        Returns:
            List of available theme names.
        """
        themes = list(self.predefined_themes.keys())
        
        # Add custom themes from files
        for theme_file in self.themes_dir.glob("*.json"):
            theme_name = theme_file.stem
            if theme_name not in themes:
                themes.append(theme_name)
        
        return sorted(themes)
    
    def get_theme_preview(self, theme_name: str) -> Dict[str, Any]:
        """Get theme preview information.
        
        Args:
            theme_name: Name of the theme.
            
        Returns:
            Dictionary containing theme preview data.
        """
        theme = self.get_theme(theme_name)
        
        return {
            "name": theme.name,
            "type": theme.type.value,
            "color_scheme": theme.color_scheme.value,
            "primary_color": theme.colors.primary,
            "secondary_color": theme.colors.secondary,
            "background_color": theme.colors.background,
            "text_color": theme.colors.text,
            "has_branding": bool(theme.branding.logo_url or theme.branding.company_name),
            "has_custom_css": bool(theme.custom_css),
            "metadata": theme.metadata
        }
    
    def apply_branding(self, theme: Theme, branding_config: Dict[str, Any]) -> Theme:
        """Apply branding configuration to theme.
        
        Args:
            theme: Theme to apply branding to.
            branding_config: Branding configuration.
            
        Returns:
            Theme with applied branding.
        """
        for key, value in branding_config.items():
            if hasattr(theme.branding, key):
                setattr(theme.branding, key, value)
        
        return theme
    
    def _setup_themes_directory(self, themes_dir: Optional[str]) -> Path:
        """Setup themes directory.
        
        Args:
            themes_dir: Custom themes directory path.
            
        Returns:
            Path to themes directory.
        """
        if themes_dir:
            themes_path = Path(themes_dir)
        else:
            # Default to themes directory in project root
            current_dir = Path(__file__).parent.parent.parent
            themes_path = current_dir / "themes"
        
        themes_path.mkdir(parents=True, exist_ok=True)
        return themes_path
    
    def _load_predefined_themes(self) -> Dict[str, Theme]:
        """Load predefined themes.
        
        Returns:
            Dictionary of predefined themes.
        """
        themes = {}
        
        # Default light theme
        themes["default"] = Theme(
            name="default",
            type=ThemeType.LIGHT,
            color_scheme=ColorScheme.DEFAULT
        )
        
        # Dark theme
        themes["dark"] = Theme(
            name="dark",
            type=ThemeType.DARK,
            color_scheme=ColorScheme.DEFAULT
        )
        
        # Corporate theme
        corporate_colors = ColorPalette(
            primary="#1f4e79",
            secondary="#2e86ab",
            accent="#f18f01",
            background="#ffffff",
            surface="#f5f7fa",
            text="#2c3e50"
        )
        themes["corporate"] = Theme(
            name="corporate",
            type=ThemeType.LIGHT,
            color_scheme=ColorScheme.CORPORATE,
            colors=corporate_colors
        )
        
        # Modern theme
        modern_colors = ColorPalette(
            primary="#667eea",
            secondary="#764ba2",
            accent="#f093fb",
            background="#ffffff",
            surface="#f8fafc",
            text="#1a202c"
        )
        themes["modern"] = Theme(
            name="modern",
            type=ThemeType.LIGHT,
            color_scheme=ColorScheme.MODERN,
            colors=modern_colors
        )
        
        # Minimal theme
        minimal_colors = ColorPalette(
            primary="#000000",
            secondary="#666666",
            accent="#ff6b6b",
            background="#ffffff",
            surface="#fafafa",
            text="#333333"
        )
        themes["minimal"] = Theme(
            name="minimal",
            type=ThemeType.LIGHT,
            color_scheme=ColorScheme.MINIMAL,
            colors=minimal_colors
        )
        
        # High contrast theme
        high_contrast_colors = ColorPalette(
            primary="#000000",
            secondary="#0066cc",
            accent="#ff0000",
            background="#ffffff",
            surface="#f0f0f0",
            text="#000000"
        )
        themes["high_contrast"] = Theme(
            name="high_contrast",
            type=ThemeType.LIGHT,
            color_scheme=ColorScheme.HIGH_CONTRAST,
            colors=high_contrast_colors
        )
        
        # Amazon theme
        amazon_colors = ColorPalette(
            primary="#232f3e",
            secondary="#ff9900",
            accent="#146eb4",
            background="#ffffff",
            surface="#f3f3f3",
            text="#0f1111"
        )
        themes["amazon"] = Theme(
            name="amazon",
            type=ThemeType.LIGHT,
            color_scheme=ColorScheme.AMAZON,
            colors=amazon_colors
        )
        
        return themes
    
    def _load_theme_from_file(self, theme_file: Path) -> Theme:
        """Load theme from JSON file.
        
        Args:
            theme_file: Path to theme file.
            
        Returns:
            Loaded theme.
            
        Raises:
            ReportGenerationError: If loading fails.
        """
        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            return Theme.from_dict(theme_data)
            
        except Exception as e:
            raise ReportGenerationError(f"Failed to load theme from {theme_file}: {e}")
    
    def _apply_customizations(self, theme: Theme, customizations: Dict[str, Any]) -> None:
        """Apply customizations to theme.
        
        Args:
            theme: Theme to customize.
            customizations: Customizations to apply.
        """
        for section, changes in customizations.items():
            if section == "colors" and isinstance(changes, dict):
                for key, value in changes.items():
                    if hasattr(theme.colors, key):
                        setattr(theme.colors, key, value)
            
            elif section == "layout" and isinstance(changes, dict):
                for key, value in changes.items():
                    if hasattr(theme.layout, key):
                        setattr(theme.layout, key, value)
            
            elif section == "branding" and isinstance(changes, dict):
                for key, value in changes.items():
                    if hasattr(theme.branding, key):
                        setattr(theme.branding, key, value)
            
            elif section == "custom_css" and isinstance(changes, str):
                theme.custom_css = changes
            
            elif section == "type" and isinstance(changes, str):
                theme.type = ThemeType(changes)


class ReportCustomizer:
    """Customizer for report appearance and content.
    
    Provides functionality for customizing report layout, content sections,
    and visual appearance beyond basic theming.
    """
    
    def __init__(self, theme_manager: ThemeManager) -> None:
        """Initialize report customizer.
        
        Args:
            theme_manager: Theme manager instance.
        """
        self.theme_manager = theme_manager
    
    def customize_report_layout(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Customize report layout configuration.
        
        Args:
            config: Layout customization configuration.
            
        Returns:
            Updated layout configuration.
        """
        layout_config = {
            "show_navigation": config.get("show_navigation", True),
            "show_summary": config.get("show_summary", True),
            "show_charts": config.get("show_charts", True),
            "show_detailed_metrics": config.get("show_detailed_metrics", True),
            "show_trends": config.get("show_trends", True),
            "sections_order": config.get("sections_order", [
                "summary", "metrics", "trends", "charts", "details"
            ]),
            "grid_columns": config.get("grid_columns", "auto-fit"),
            "responsive_breakpoints": config.get("responsive_breakpoints", {
                "mobile": "768px",
                "tablet": "1024px",
                "desktop": "1200px"
            })
        }
        
        return layout_config
    
    def generate_custom_css(self, customizations: Dict[str, Any]) -> str:
        """Generate custom CSS from customizations.
        
        Args:
            customizations: CSS customizations.
            
        Returns:
            Generated CSS string.
        """
        css_parts = []
        
        # Custom selectors and styles
        if "custom_styles" in customizations:
            for selector, styles in customizations["custom_styles"].items():
                css_parts.append(f"{selector} {{")
                for property_name, value in styles.items():
                    css_parts.append(f"  {property_name}: {value};")
                css_parts.append("}")
        
        # Responsive overrides
        if "responsive" in customizations:
            for breakpoint, styles in customizations["responsive"].items():
                css_parts.append(f"@media (max-width: {breakpoint}) {{")
                for selector, properties in styles.items():
                    css_parts.append(f"  {selector} {{")
                    for prop, value in properties.items():
                        css_parts.append(f"    {prop}: {value};")
                    css_parts.append("  }")
                css_parts.append("}")
        
        # Print styles
        if "print" in customizations:
            css_parts.append("@media print {")
            for selector, properties in customizations["print"].items():
                css_parts.append(f"  {selector} {{")
                for prop, value in properties.items():
                    css_parts.append(f"    {prop}: {value};")
                css_parts.append("  }")
            css_parts.append("}")
        
        return "\n".join(css_parts)
    
    def apply_content_customizations(self, template_data: Dict[str, Any],
                                   customizations: Dict[str, Any]) -> Dict[str, Any]:
        """Apply content customizations to template data.
        
        Args:
            template_data: Original template data.
            customizations: Content customizations.
            
        Returns:
            Customized template data.
        """
        # Custom title and descriptions
        if "title_prefix" in customizations:
            template_data["title"] = f"{customizations['title_prefix']} {template_data.get('title', '')}"
        
        if "custom_header" in customizations:
            template_data["custom_header"] = customizations["custom_header"]
        
        if "custom_footer" in customizations:
            template_data["custom_footer"] = customizations["custom_footer"]
        
        # Section visibility
        section_visibility = customizations.get("section_visibility", {})
        template_data["show_sections"] = {
            "summary": section_visibility.get("summary", True),
            "metrics": section_visibility.get("metrics", True),
            "trends": section_visibility.get("trends", True),
            "charts": section_visibility.get("charts", True),
            "details": section_visibility.get("details", True)
        }
        
        # Custom sections
        if "custom_sections" in customizations:
            template_data["custom_sections"] = customizations["custom_sections"]
        
        return template_data