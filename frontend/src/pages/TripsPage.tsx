import { useState } from 'react';

import { getErrorMessage } from '@/api/errors';
import { Card, CardHeader } from '@/components/Card';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { PageHeader } from '@/components/PageHeader';
import { TripForm } from '@/features/trips/TripForm';
import { TripHistory } from '@/features/trips/TripHistory';
import { useCreateTrip, useDeleteTrip, useUpdateTrip } from '@/features/trips/useTrips';
import { toFormValues } from '@/features/trips/validation';
import { cn } from '@/lib/cn';
import type { Trip, TripInput } from '@/types/trip';

export function TripsPage() {
  const [editing, setEditing] = useState<Trip | null>(null);
  const [toDelete, setToDelete] = useState<Trip | null>(null);
  // Bumping the key remounts the form, which resets it after a successful save.
  const [formKey, setFormKey] = useState(0);

  const createTrip = useCreateTrip();
  const updateTrip = useUpdateTrip();
  const deleteTrip = useDeleteTrip();
  const activeMutation = editing ? updateTrip : createTrip;

  function resetForm() {
    setEditing(null);
    createTrip.reset();
    updateTrip.reset();
    setFormKey((key) => key + 1);
  }

  function handleSubmit(input: TripInput) {
    if (editing) {
      updateTrip.mutate({ id: editing.id, input }, { onSuccess: resetForm });
    } else {
      createTrip.mutate(input, { onSuccess: resetForm });
    }
  }

  function handleEdit(trip: Trip) {
    createTrip.reset();
    updateTrip.reset();
    setEditing(trip);
    setFormKey((key) => key + 1);
  }

  function handleConfirmDelete() {
    if (!toDelete) return;
    deleteTrip.mutate(toDelete.id, {
      onSuccess: () => {
        if (editing?.id === toDelete.id) resetForm();
        setToDelete(null);
      },
    });
  }

  function handleCancelDelete() {
    setToDelete(null);
    deleteTrip.reset();
  }

  return (
    <>
      <PageHeader
        title="Your trips"
        description="Save your journeys and see how your choice of transport affects your carbon footprint."
      />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        {/* Sticky on wide screens, but it scrolls itself when taller than the window, so the
            submit button is always reachable. */}
        <Card
          aria-label={editing ? 'Edit trip' : 'New trip'}
          className={cn(
            'transition-shadow lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto',
            editing && 'border-emerald-500 ring-4 ring-emerald-100',
          )}
        >
          <CardHeader
            title={
              editing ? (
                <span className="flex items-center gap-2">
                  Edit trip
                  <span className="rounded-full bg-emerald-600 px-2 py-0.5 text-xs font-medium text-white">
                    Editing
                  </span>
                </span>
              ) : (
                'New trip'
              )
            }
            description={
              editing
                ? `${editing.origin} → ${editing.destination}`
                : 'Where from, where to, and how you travel.'
            }
          />
          <div className="px-5 py-5 sm:px-6">
            <TripForm
              key={formKey}
              initialValues={editing ? toFormValues(editing) : undefined}
              submitLabel={editing ? 'Save changes' : 'Add trip'}
              isSubmitting={activeMutation.isPending}
              serverError={activeMutation.isError ? getErrorMessage(activeMutation.error) : null}
              onSubmit={handleSubmit}
              onCancel={editing ? resetForm : undefined}
            />
          </div>
        </Card>

        <TripHistory editingId={editing?.id ?? null} onEdit={handleEdit} onDelete={setToDelete} />
      </div>

      <ConfirmDialog
        open={toDelete !== null}
        title="Delete this trip?"
        description={
          toDelete
            ? `The trip ${toDelete.origin} → ${toDelete.destination} will be permanently removed from your history.`
            : ''
        }
        confirmLabel="Delete"
        isPending={deleteTrip.isPending}
        error={deleteTrip.isError ? getErrorMessage(deleteTrip.error) : null}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
      />
    </>
  );
}
