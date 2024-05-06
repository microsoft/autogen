"use client";

import React, { useRef, useState } from 'react';

import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

import { styled } from '@mui/material/styles';
import { Avatar, Box, Container } from '@mui/material';
import Badge, { BadgeProps } from '@mui/material/Badge';
import { Typography } from '@mui/material';
import List from '@mui/material/List';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import KeyboardArrowDown from '@mui/icons-material/KeyboardArrowDown';
import PersonIcon from '@mui/icons-material/Person';
import ListItemIcon from '@mui/material/ListItemIcon';
import { Title } from '@refinedev/mui';

const GreenStyledBadge = styled(Badge)(({ theme }) => ({
    '& .MuiBadge-badge': {
        backgroundColor: '#44b700',
        color: '#44b700',
        boxShadow: `0 0 0 2px ${theme.palette.background.paper}`,
        '&::after': {
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            animation: 'ripple 1.2s infinite ease-in-out',
            border: '1px solid currentColor',
            content: '""',
        },
    },
    '@keyframes ripple': {
        '0%': {
            transform: 'scale(.8)',
            opacity: 1,
        },
        '100%': {
            transform: 'scale(2.4)',
            opacity: 0,
        },
    },
}));

const RedStyledBadge = styled(Badge)(({ theme }) => ({
    '& .MuiBadge-badge': {
        backgroundColor: 'red',
        color: '#44b700',
        boxShadow: `0 0 0 2px ${theme.palette.background.paper}`,
        '&::after': {
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            animation: 'ripple 1.2s infinite ease-in-out',
            border: '1px solid currentColor',
            content: '""',
        },
    },
    '@keyframes ripple': {
        '0%': {
            transform: 'scale(.8)',
            opacity: 1,
        },
        '100%': {
            transform: 'scale(2.4)',
            opacity: 0,
        },
    },
}));

export default function StakeholderList() {
    const [open, setOpen] = React.useState(false);

    console.log(`[Marketing] Rendering.`);
    return (
        <Box sx={{ display: 'flex' }}>
            <List sx={{ width: '100%', maxWidth: 360, bgcolor: 'background.paper' }}>
                <ListItemButton
                    alignItems="flex-start"
                    onClick={() => setOpen(!open)}
                    sx={{
                        px: 3,
                        pt: 2.5,
                        pb: open ? 0 : 2.5,
                        '&:hover, &:focus': { '& #arrowdownicon': { opacity: open ? 1 : 0 } },
                    }}
                >
                    <ListItemIcon sx={{ my: 0, opacity: 1, class: "menuicon" }}>
                        <PersonIcon />
                    </ListItemIcon>
                    <ListItemText
                        primary="Auditor"
                        primaryTypographyProps={{
                            fontSize: 15,
                            fontWeight: 'medium',
                            lineHeight: '20px',
                            mb: '2px',
                        }}
                        secondary="Auditing rules"
                        secondaryTypographyProps={{
                            noWrap: true,
                            fontSize: 12,
                            lineHeight: '16px',
                            color: open ? 'rgba(0,0,0,0)' : 'rgba(255,255,255,0.5)',
                        }}
                        sx={{ my: 0 }}
                    />
                    <KeyboardArrowDown
                        id="arrowdownicon"
                        sx={{
                            mr: -1,
                            opacity: 0,
                            transform: open ? 'rotate(-180deg)' : 'rotate(0)',
                            transition: '0.2s',
                        }}
                    />
                </ListItemButton>
                {open && (
                    <Box>
                        <ListItemButton alignItems="flex-start">
                            <ListItemAvatar>
                                <Avatar alt="Language check" src="/static/check.png" />
                            </ListItemAvatar>
                            <ListItemText
                                primary="Language check"
                            />
                        </ListItemButton>
                        <ListItemButton alignItems="flex-start">
                            <ListItemAvatar>
                                <Avatar alt="Financial check" src="/static/check.png" />
                            </ListItemAvatar>
                            <ListItemText
                                primary="Financial check"
                            />
                        </ListItemButton>
                        <ListItemButton alignItems="flex-start">
                            <ListItemAvatar>
                                <Avatar alt="Auto approval" src="/static/check.png" />
                            </ListItemAvatar>
                            <ListItemText
                                primary="Auto approval"
                            />
                        </ListItemButton>
                    </Box>
                )}
                {open && (
                    <p>Questions? These are relevant stakeholders for you:</p>
                )}
                {open && (
                    <Box>
                    <ListItemButton alignItems="flex-start">
                        <ListItemAvatar>
                            <RedStyledBadge
                                overlap="circular"
                                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                                variant="dot"
                            >
                                <Avatar alt="Lawrence Law" src="/static/face2.jpg" />
                            </RedStyledBadge>
                        </ListItemAvatar>
                        <ListItemText
                            primary="Lina Maria"
                            secondary={
                                <React.Fragment>
                                    <Typography
                                        sx={{ display: 'inline' }}
                                        component="span"
                                        variant="body2"
                                        color="text.primary"
                                    >
                                        General Attorney
                                    </Typography>
                                </React.Fragment>
                            }
                        />
                    </ListItemButton>
                    <ListItemButton alignItems="flex-start">
                        <ListItemAvatar>
                            <GreenStyledBadge
                                overlap="circular"
                                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                                variant="dot"
                            >
                                <Avatar alt="Remy Sharp" src="/static/face.jpg" />
                            </GreenStyledBadge>
                        </ListItemAvatar>
                        <ListItemText
                            primary="Lawrence Gevaert"
                            secondary={
                                <React.Fragment>
                                    <Typography
                                        sx={{ display: 'inline' }}
                                        component="span"
                                        variant="body2"
                                        color="text.primary"
                                    >
                                        Marketing Manager
                                    </Typography>
                                </React.Fragment>
                            }
                        />
                    </ListItemButton>
                    </Box>
                )}
            </List>
        </Box>
    );
}