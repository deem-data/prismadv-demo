import { StateCreator } from 'zustand';
import type { AppState, CodeFile, Dataset } from '@/types';
import apiClient from '@/api';

export interface FilesSlice {
  taskFile: CodeFile | null;
  dataset: Dataset | null;
  uploadTaskFile: (file: File) => Promise<void>;
  uploadDataset: (file: File) => Promise<void>;
}

export const createFilesSlice: StateCreator<
  AppState,
  [],
  [],
  FilesSlice
> = (set, get) => ({
  taskFile: null,
  dataset: null,

  uploadTaskFile: async (file: File) => {
    try {
      const taskFile = await apiClient.uploadTaskFile(file);
      set({ taskFile, code: taskFile.content });

      get().addToast({
        type: 'success',
        message: `Task file "${taskFile.name}" uploaded successfully`,
      });
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Failed to upload task file: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
      throw error;
    }
  },

  uploadDataset: async (file: File) => {
    try {
      const dataset = await apiClient.uploadDataset(file);
      set({ dataset });
      // Clear any Deequ suggestions from the previous dataset
      get().clearDeequSuggestions();

      // Fetch completeness metrics right after loading
      apiClient.getDataQualityMetrics(dataset.id)
        .then((qualityMetrics) => set({ dataQualityMetrics: qualityMetrics }))
        .catch(() => {});

      get().addToast({
        type: 'success',
        message: `Dataset "${dataset.name}" uploaded successfully`,
      });
    } catch (error) {
      get().addToast({
        type: 'error',
        message: `Failed to upload dataset: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
      throw error;
    }
  },
});
